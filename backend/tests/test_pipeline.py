"""In-process pipeline with the offline provider, including degraded mode and output sanitizing."""

from __future__ import annotations

import pytest

from letterlens.config import Settings
from letterlens.domain import ExplanationDraft, FactLabel, LetterStatus, NextStep, SummarySentence
from letterlens.llm import Gateway, InMemoryLedger, Task
from letterlens.llm.providers.fake import FakeProvider
from letterlens.ml.classifier import default_model
from letterlens.pipeline.runner import EXPLAIN_ONLY, InProcessRunner
from letterlens.pipeline.state import InMemoryStateStore, PipelineState
from letterlens.pipeline.steps import PipelineDeps, sanitize_explanation
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.pii import PiiVault
from letterlens.synthetic import generate_corpus, to_document


def make_runner(provider: FakeProvider) -> tuple[InProcessRunner, InMemoryStateStore]:
    settings = Settings(env="test")
    deps = PipelineDeps(
        Gateway(provider, settings, InMemoryLedger(), sleep=lambda _: None),
        HybridRetriever(),
        default_model(),
    )
    store = InMemoryStateStore()
    return InProcessRunner(store, lambda: deps), store


def submit(store: InMemoryStateStore, n: int = 0) -> str:
    letter = generate_corpus(1)[n]
    store.save_state(PipelineState(letter_id=letter.id, owner_id="u1", document=to_document(letter)))
    return letter.id


def test_full_run() -> None:
    runner, store = make_runner(FakeProvider())
    lid = submit(store)
    runner.start(lid)
    assert store.status[lid][0] is LetterStatus.READY
    state = store.load_state(lid)
    assert state.classification and state.classification.letter_type.value == "tax"
    assert state.facts and state.facts.grounding_rate == 1.0
    assert state.passages and state.passages[0].doc_id == "tax-objection"
    exp = state.explanations["en"]
    assert exp.summary and exp.disclaimer and not state.degraded


def test_llm_never_sees_recipient_name() -> None:
    provider = FakeProvider()
    runner, store = make_runner(provider)
    lid = submit(store)
    name = next(x for x in store.load_state(lid).document.lines if x.text == "Yusuf Öztürk")
    runner.start(lid)
    for request in provider.calls:
        assert name.text not in request.user


def test_degraded_mode_when_llm_fails() -> None:
    runner, store = make_runner(FakeProvider(fail_tasks={Task.EXTRACT, Task.EXPLAIN}))
    lid = submit(store)
    runner.start(lid)
    state = store.load_state(lid)
    assert store.status[lid][0] is LetterStatus.READY
    assert state.degraded
    assert {r.split(":")[0] for r in state.degraded_reasons} == {"extract", "explain"}
    assert state.facts and state.facts.deadlines


def test_second_language_run() -> None:
    runner, store = make_runner(FakeProvider())
    lid = submit(store)
    runner.start(lid)
    runner.start(lid, EXPLAIN_ONLY, "de")
    assert set(store.load_state(lid).explanations) == {"en", "de"}


def test_other_languages_translate_the_checked_english_text() -> None:
    provider = FakeProvider()
    runner, store = make_runner(provider)
    lid = submit(store)
    runner.start(lid)
    runner.start(lid, EXPLAIN_ONLY, "tr")
    state = store.load_state(lid)
    en, tr = state.explanations["en"], state.explanations["tr"]
    # Same content in the same order: every sentence keeps its line links, every step its citations.
    assert [s.line_ids for s in tr.summary] == [s.line_ids for s in en.summary]
    assert [s.citation_ids for s in tr.next_steps] == [s.citation_ids for s in en.next_steps]
    assert tr.citations == en.citations
    assert tr.deadline_labels.keys() == en.deadline_labels.keys()
    assert all(s.text.startswith("[tr] ") for s in tr.summary)
    assert tr.counselling_hint != en.counselling_hint  # localized texts, not translated by the model
    translate_calls = [c for c in provider.calls if c.task is Task.TRANSLATE_EXPLANATION]
    assert len(translate_calls) == 1
    explain_calls = [c for c in provider.calls if c.task is Task.EXPLAIN]
    assert len(explain_calls) == 1  # the letter is explained once


def test_translation_never_sees_recipient_name() -> None:
    provider = FakeProvider()
    runner, store = make_runner(provider)
    lid = submit(store)
    name = next(x for x in store.load_state(lid).document.lines if x.text == "Yusuf Öztürk").text
    state = store.load_state(lid)
    state.language = "ar"
    store.save_state(state)
    runner.start(lid)
    calls = [c for c in provider.calls if c.task is Task.TRANSLATE_EXPLANATION]
    assert calls
    for request in calls:
        assert name not in request.user and "Öztürk" not in request.user


class _DroppingTranslator(FakeProvider):
    """Returns one summary item too few, like a model that merges two sentences."""

    @staticmethod
    def _translate_explanation(ctx: dict[str, object]) -> dict[str, object]:
        out = FakeProvider._translate_explanation(ctx)  # type: ignore[arg-type]
        out["summary"] = out["summary"][:-1]
        return out


def test_incomplete_translation_falls_back_to_direct_writing() -> None:
    provider = _DroppingTranslator()
    runner, store = make_runner(provider)
    lid = submit(store)
    runner.start(lid)
    runner.start(lid, EXPLAIN_ONLY, "uk")
    state = store.load_state(lid)
    uk = state.explanations["uk"]
    assert len(uk.summary) > 0
    assert not any(
        s.text.startswith("[uk]") for s in uk.summary
    )  # written directly, not the broken translation
    assert [c.task for c in provider.calls].count(Task.EXPLAIN) == 2


def test_failure_marks_letter_failed() -> None:
    runner, store = make_runner(FakeProvider())
    store.save_state(PipelineState(letter_id="x", owner_id="u1", document=to_document(generate_corpus(1)[0])))
    runner.start("missing-id")
    assert store.status["missing-id"][0] is LetterStatus.FAILED


@pytest.fixture
def ready_state() -> PipelineState:
    runner, store = make_runner(FakeProvider())
    lid = submit(store)
    runner.start(lid)
    return store.load_state(lid)


def test_sanitizer_drops_advice_invented_numbers_and_uncited_steps(ready_state: PipelineState) -> None:
    assert ready_state.facts and ready_state.passages
    draft = ExplanationDraft(
        headline="Tax decision https://evil.example",
        letter_kind="Tax letter",
        summary=[
            SummarySentence(text="You must pay 1.523,00 EUR.", line_ids=["p1-l14", "p9-l9"]),
            SummarySentence(text="You should object to this decision.", line_ids=[]),
            SummarySentence(text="You must pay 9.999,00 EUR.", line_ids=[]),
        ],
        next_steps=[
            NextStep(text="An objection is free.", citation_ids=["c1", "c99"]),
            NextStep(text="Ask your neighbour.", citation_ids=[]),
        ],
        deadline_labels=[FactLabel(id="d1", label="Pay"), FactLabel(id="d42", label="x")],
        amount_labels=[],
    )
    exp, stats = sanitize_explanation(draft, ready_state, ready_state.passages, "en", "m", PiiVault())
    assert [s.text for s in exp.summary] == ["You must pay 1.523,00 EUR."]
    assert exp.summary[0].line_ids == ["p1-l14"]
    assert [s.citation_ids for s in exp.next_steps] == [["c1"]]
    assert "http" not in exp.headline
    assert set(exp.deadline_labels) == {"d1"}
    assert stats == {"dropped_advisory": 1, "dropped_numbers": 1, "dropped_uncited": 1}
    assert [c.id for c in exp.citations] == ["c1"]


def test_amounts_with_space_thousands_separator_are_recognized() -> None:
    from letterlens.pipeline.steps import unsupported_numbers

    allowed = {"1.092,50", "1092,50", "1092.50", "1092", "2026"}
    for text in [
        "Ви отримуватимете 1 092,50 євро.",
        "Вы получите 1\u00a0092,50 €.",
        "Montant : 1\u202f092,50 €",
    ]:
        assert unsupported_numbers(text, allowed) == [], text
    assert unsupported_numbers("Вы получите 1 093,50 €.", allowed) == ["1093,50"]

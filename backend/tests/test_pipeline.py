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



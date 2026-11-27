"""Pipeline steps. Each step is a pure function of (state, deps) -> state.

The same functions run in-process (local development, tests) and inside the
Step Functions worker Lambda (production). Steps never log letter text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from letterlens.domain import (
    Citation,
    Explanation,
    ExplanationDraft,
    Extraction,
    LetterType,
    NextStep,
    Passage,
    SummarySentence,
    VerifiedFacts,
)
from letterlens.extraction.rules import extract_with_rules
from letterlens.grounding.german import find_amounts, find_dates, parse_amount
from letterlens.grounding.verifier import verify
from letterlens.i18n import COUNSELLING_HINT, DISCLAIMER, languages, localized
from letterlens.llm import Gateway, Task
from letterlens.llm import prompts as P
from letterlens.llm.outputs import ExplanationTranslation
from letterlens.llm.providers.fake import FakeProvider
from letterlens.llm.types import LLMError
from letterlens.ml.classifier import LinearModel
from letterlens.pipeline.state import PipelineState
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.guardrail import is_advisory_output, neutralize_injections
from letterlens.safety.pii import PiiVault

log = logging.getLogger(__name__)

_SPACE_GROUPED = re.compile(r"(?<![\d.,])\d{1,3}(?:[ \u00a0\u202f\u2009]\d{3})+(?!\d)")
_URL = re.compile(r"https?://\S+|www\.\S+")
_EASTERN_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_NUMBER = re.compile(r"\d[\d.,]*\d|\d")


@dataclass(frozen=True)
class PipelineDeps:
    gateway: Gateway
    retriever: HybridRetriever
    classifier: LinearModel


# --------------------------------------------------------------------------


def classify(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    state.classification = deps.classifier.classify(state.document.plain_text())
    return state


def extract(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    letter_type = state.classification.letter_type if state.classification else LetterType.OTHER
    vault = PiiVault()
    cleaned, _ = neutralize_injections(state.document)
    redacted = vault.redact_document(cleaned)
    try:
        draft = deps.gateway.generate(
            Task.EXTRACT,
            Extraction,
            P.extract_system(letter_type),
            P.extract_user(redacted.as_numbered_text()),
            P.EXTRACT_VERSION,
            context={"document": redacted.model_dump(mode="json")},
            user_id=state.owner_id,
            letter_id=state.letter_id,
        )
        state.extraction = Extraction.model_validate(vault.restore(draft.model_dump(mode="json")))
    except LLMError as exc:
        log.warning("extract degraded", extra={"letter_id": state.letter_id, "error": type(exc).__name__})
        state.extraction = extract_with_rules(cleaned)
        state.mark_degraded(f"extract:{type(exc).__name__}")
    return state


def verify_step(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    assert state.extraction is not None
    state.facts = verify(state.extraction, state.document)
    return state


def retrieval_query(state: PipelineState) -> str:
    facts = state.facts
    parts: list[str] = []
    if facts is not None:
        parts += [facts.subject.value or "", facts.sender.value or ""]
        parts += [d.description for d in facts.deadlines]
        parts += [a.description for a in facts.required_actions]
    # German key terms (Widerspruch, Einspruch, Mahnbescheid ...) carry most of the signal.
    parts.append(state.document.plain_text()[:2500])
    return "\n".join(p for p in parts if p)


def retrieve(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    letter_type = state.classification.letter_type if state.classification else LetterType.OTHER
    state.passages = deps.retriever.search(retrieval_query(state), letter_type, k=4)
    return state


# --------------------------------------------------------------------------
# Explanation and its validation
# --------------------------------------------------------------------------


def _facts_for_prompt(facts: VerifiedFacts, vault: PiiVault) -> dict[str, Any]:
    raw = json.dumps(facts.model_dump(mode="json"), ensure_ascii=False)
    redacted: dict[str, Any] = json.loads(vault.redact_text(raw))
    return redacted


def number_forms(token: str) -> set[str]:
    """All normalized readings of a number token: raw, German amount, English amount, date."""
    tok = token.strip(".,")
    forms = {tok}
    dates = find_dates(tok)
    if dates:
        forms.add(dates[0].isoformat())
    if re.fullmatch(r"\d+\.\d{1,2}", tok):  # English decimal: 1523.00
        forms.add(str(Decimal(tok).quantize(Decimal("0.01"))))
    if re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d{1,2})?", tok):  # English thousands: 1,523.00
        forms.add(str(Decimal(tok.replace(",", "")).quantize(Decimal("0.01"))))
    if not dates and (german := parse_amount(tok)) is not None and ("," in tok or "." in tok):
        forms.add(str(german))
    if tok.isdigit():
        forms.add(str(int(tok)))
    return forms


def allowed_numbers(state: PipelineState) -> set[str]:
    """Normalized numbers that an explanation may mention: from the letter and verified facts."""
    text = state.document.plain_text()
    allowed: set[str] = set()
    for tok in _NUMBER.findall(text):
        allowed |= number_forms(tok)
    for d in find_dates(text):
        allowed |= {d.isoformat(), str(d.day), str(d.month), str(d.year)}
    for a in find_amounts(text):
        allowed |= {str(a), str(int(a))}
    if state.facts:
        for dl in state.facts.deadlines:
            if dl.due_date:
                dd = dl.due_date
                allowed |= {dd.isoformat(), str(dd.day), str(dd.month), str(dd.year)}
    allowed |= {str(n) for n in range(0, 32)}  # counts and day numbers ("2 weeks", "the 4th day")
    return allowed


def unsupported_numbers(text: str, allowed: set[str]) -> list[str]:
    """Numbers in generated text that occur neither in the letter nor in the verified facts."""
    normalized = text.translate(_EASTERN_DIGITS).replace("\u066b", ",").replace("\u066c", ".")
    # "1 092,50" (space, no-break space or thin space as thousands separator, as in uk, ru, fr).
    normalized = _SPACE_GROUPED.sub(lambda m: re.sub(r"\s", "", m[0]), normalized)
    return [tok for tok in _NUMBER.findall(normalized) if not number_forms(tok) & allowed]


def sanitize_explanation(
    draft: ExplanationDraft,
    state: PipelineState,
    passages: list[Passage],
    language: str,
    model: str,
    vault: PiiVault,
) -> tuple[Explanation, dict[str, int]]:
    """Enforce the output contract. Returns the explanation and counters for metrics."""
    assert state.facts is not None
    line_ids = state.document.line_map().keys()
    passage_ids = {p.id for p in passages}
    allowed = allowed_numbers(state)
    stats = {"dropped_advisory": 0, "dropped_numbers": 0, "dropped_uncited": 0}

    def clean(text: str) -> str:
        restored = vault.restore(text)
        assert isinstance(restored, str)
        return _URL.sub("", restored).strip()

    summary: list[SummarySentence] = []
    for s in draft.summary:
        text = clean(s.text)
        if is_advisory_output(text):
            stats["dropped_advisory"] += 1
            continue
        if unsupported_numbers(text, allowed):
            stats["dropped_numbers"] += 1
            continue
        summary.append(SummarySentence(text=text, line_ids=[i for i in s.line_ids if i in line_ids]))

    steps: list[NextStep] = []
    for step in draft.next_steps:
        cites = [c for c in step.citation_ids if c in passage_ids]
        text = clean(step.text)
        if not cites:
            stats["dropped_uncited"] += 1
            continue
        if is_advisory_output(text):
            stats["dropped_advisory"] += 1
            continue
        if unsupported_numbers(text, allowed):
            stats["dropped_numbers"] += 1
            continue
        steps.append(NextStep(text=text, citation_ids=cites))

    deadline_ids = {d.id for d in state.facts.deadlines}
    amount_ids = {a.id for a in state.facts.amounts}
    used = {c for s in steps for c in s.citation_ids}
    citations = [
        Citation(
            id=p.id,
            title=p.title,
            source_url=p.source_url,
            source_name=p.source_name,
            checked_on=p.checked_on,
        )
        for p in passages
        if p.id in used
    ]
    explanation = Explanation(
        language=language,
        headline=clean(draft.headline),
        letter_kind=clean(draft.letter_kind),
        summary=summary,
        next_steps=steps,
        deadline_labels={x.id: clean(x.label) for x in draft.deadline_labels if x.id in deadline_ids},
        amount_labels={x.id: clean(x.label) for x in draft.amount_labels if x.id in amount_ids},
        citations=citations,
        counselling_hint=localized(COUNSELLING_HINT, language),
        disclaimer=localized(DISCLAIMER, language),
        model=model,
    )
    return explanation, stats


CANONICAL_LANGUAGE = "en"


class TranslationMismatchError(Exception):
    """The translation did not return exactly one item for each source item."""


def explain(state: PipelineState, deps: PipelineDeps, language: str | None = None) -> PipelineState:
    """Explain the letter in English, check it, then translate the checked text.

    Every language shows the same content: the English explanation is grounded and sanitized once,
    and the translation maps item by item, so line links, citations and fact ids stay identical.
    If the translation fails, the explanation is written directly in the target language.
    """
    assert state.facts is not None
    language = language or state.language
    lang = languages().get(language) or languages()[CANONICAL_LANGUAGE]
    if lang.code == CANONICAL_LANGUAGE:
        return _explain_direct(state, deps, lang.code)
    if CANONICAL_LANGUAGE not in state.explanations:
        state = _explain_direct(state, deps, CANONICAL_LANGUAGE)
    source = state.explanations[CANONICAL_LANGUAGE]
    if source.model == "template":
        return state  # The model is not available; the English template is the result.
    try:
        state.explanations[lang.code] = _translate_explanation(state, deps, source, lang.code)
    except (LLMError, TranslationMismatchError) as exc:
        log.warning(
            "translation failed, writing directly",
            extra={"letter_id": state.letter_id, "language": lang.code, "error": type(exc).__name__},
        )
        state = _explain_direct(state, deps, lang.code)
    return state


def _translate_explanation(
    state: PipelineState, deps: PipelineDeps, source: Explanation, language: str
) -> Explanation:
    lang = languages()[language]
    vault = PiiVault()
    cleaned, _ = neutralize_injections(state.document)
    vault.redact_document(cleaned)  # Learns the names and addresses of this letter.
    hide = vault.reapply
    headline, kind = hide(source.headline), hide(source.letter_kind)
    summary_src = [hide(x.text) for x in source.summary]
    steps_src = [hide(x.text) for x in source.next_steps]
    deadline_src = {k: hide(v) for k, v in source.deadline_labels.items()}
    amount_src = {k: hide(v) for k, v in source.amount_labels.items()}
    numbered = {
        "headline": headline,
        "letter_kind": kind,
        "summary": [{"index": i, "text": t} for i, t in enumerate(summary_src)],
        "next_steps": [{"index": i, "text": t} for i, t in enumerate(steps_src)],
        "deadline_labels": [{"id": k, "label": v} for k, v in deadline_src.items()],
        "amount_labels": [{"id": k, "label": v} for k, v in amount_src.items()],
    }
    flat = {
        "headline": headline,
        "letter_kind": kind,
        "summary": summary_src,
        "next_steps": steps_src,
        "deadline_labels": deadline_src,
        "amount_labels": amount_src,
    }
    out = deps.gateway.generate(
        Task.TRANSLATE_EXPLANATION,
        ExplanationTranslation,
        P.translate_explanation_system(lang.name),
        f"<explanation>\n{json.dumps(numbered, ensure_ascii=False)}\n</explanation>",
        P.TRANSLATE_EXPLANATION_VERSION,
        context={"source": flat, "language": language},
        user_id=state.owner_id,
        letter_id=state.letter_id,
        max_tokens=6000,
    )
    summary_t = {x.index: x.text for x in out.summary}
    steps_t = {x.index: x.text for x in out.next_steps}
    if set(summary_t) != set(range(len(source.summary))) or set(steps_t) != set(
        range(len(source.next_steps))
    ):
        raise TranslationMismatchError("item count differs")

    allowed = allowed_numbers(state)
    dropped = 0

    def clean(text: str) -> str:
        restored = vault.restore(text)
        assert isinstance(restored, str)
        return _URL.sub("", restored).strip()

    def safe(text: str) -> bool:
        return not is_advisory_output(text) and not unsupported_numbers(text, allowed)

    summary: list[SummarySentence] = []
    for i, sentence in enumerate(source.summary):
        text = clean(summary_t[i])
        if safe(text):
            summary.append(SummarySentence(text=text, line_ids=sentence.line_ids))
        else:
            dropped += 1
    steps: list[NextStep] = []
    for i, step in enumerate(source.next_steps):
        text = clean(steps_t[i])
        if safe(text):
            steps.append(NextStep(text=text, citation_ids=step.citation_ids))
        else:
            dropped += 1
    if dropped:
        log.info("translation sanitized", extra={"letter_id": state.letter_id, "dropped": dropped})
    deadline_t = {x.id: clean(x.label) for x in out.deadline_labels}
    amount_t = {x.id: clean(x.label) for x in out.amount_labels}
    return Explanation(
        language=language,
        headline=clean(out.headline),
        letter_kind=clean(out.letter_kind),
        summary=summary,
        next_steps=steps,
        deadline_labels={k: deadline_t.get(k) or v for k, v in source.deadline_labels.items()},
        amount_labels={k: amount_t.get(k) or v for k, v in source.amount_labels.items()},
        citations=source.citations,
        counselling_hint=localized(COUNSELLING_HINT, language),
        disclaimer=localized(DISCLAIMER, language),
        model=deps.gateway.models_for(Task.TRANSLATE_EXPLANATION)[0],
    )


def _explain_direct(state: PipelineState, deps: PipelineDeps, language: str) -> PipelineState:
    """Write the explanation in one language directly from the letter, facts and passages."""
    assert state.facts is not None
    lang = languages().get(language) or languages()[CANONICAL_LANGUAGE]
    passages = state.passages or []
    letter_type = state.classification.letter_type if state.classification else LetterType.OTHER
    vault = PiiVault()
    cleaned, _ = neutralize_injections(state.document)
    redacted = vault.redact_document(cleaned)
    facts_json = _facts_for_prompt(state.facts, vault)
    passages_ctx = [p.model_dump(mode="json") for p in passages]
    model_name = deps.gateway.models_for(Task.EXPLAIN)[0]
    try:
        draft = deps.gateway.generate(
            Task.EXPLAIN,
            ExplanationDraft,
            P.explain_system(lang.name),
            P.explain_user(redacted.as_numbered_text(), facts_json, passages),
            P.EXPLAIN_VERSION,
            context={
                "facts": facts_json,
                "passages": passages_ctx,
                "language": lang.code,
                "letter_type": letter_type.value,
            },
            user_id=state.owner_id,
            letter_id=state.letter_id,
            max_tokens=6000,
        )
    except LLMError as exc:
        log.warning("explain degraded", extra={"letter_id": state.letter_id, "error": type(exc).__name__})
        draft = ExplanationDraft.model_validate(
            FakeProvider._explain(
                {"facts": facts_json, "passages": passages_ctx, "letter_type": letter_type.value}
            )
        )
        state.mark_degraded(f"explain:{type(exc).__name__}")
        model_name = "template"
        lang = languages()["en"]
    explanation, stats = sanitize_explanation(draft, state, passages, lang.code, model_name, vault)
    if any(stats.values()):
        log.info("explanation sanitized", extra={"letter_id": state.letter_id, **stats})
    state.explanations[lang.code] = explanation
    return state


def finalize(state: PipelineState, deps: PipelineDeps) -> PipelineState:
    return state


STEP_FUNCTIONS = {
    "classify": classify,
    "extract": extract,
    "verify": verify_step,
    "retrieve": retrieve,
    "explain": explain,
    "finalize": finalize,
}

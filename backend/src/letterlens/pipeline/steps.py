"""Pipeline steps. Each step is a pure function of (state, deps) -> state.

The same functions run in-process (local development, tests) and inside the
Step Functions worker Lambda (production). Steps never log letter text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
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
from letterlens.grounding.german import find_amounts, find_dates
from letterlens.grounding.verifier import verify
from letterlens.i18n import COUNSELLING_HINT, DISCLAIMER, languages, localized
from letterlens.llm import Gateway, Task
from letterlens.llm import prompts as P
from letterlens.llm.providers.fake import FakeProvider
from letterlens.llm.types import LLMError
from letterlens.ml.classifier import LinearModel
from letterlens.pipeline.state import PipelineState
from letterlens.rag.retriever import HybridRetriever
from letterlens.safety.guardrail import is_advisory_output
from letterlens.safety.pii import PiiVault

log = logging.getLogger(__name__)

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
    redacted = vault.redact_document(state.document)
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
        state.extraction = extract_with_rules(state.document)
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


def allowed_numbers(state: PipelineState) -> set[str]:
    """Every number that the explanation may mention: from the letter and the verified facts."""
    text = state.document.plain_text()
    allowed = {n for n in _NUMBER.findall(text)}
    for d in find_dates(text):
        allowed |= {str(d.day), str(d.month), str(d.year), f"{d.day:02d}", f"{d.month:02d}"}
        allowed.add(d.isoformat())
    for a in find_amounts(text):
        allowed |= {str(a), str(a).replace(".", ","), str(int(a))}
    if state.facts:
        for dl in state.facts.deadlines:
            if dl.due_date:
                dd = dl.due_date
                allowed |= {dd.isoformat(), str(dd.day), str(dd.month), str(dd.year),
                            f"{dd.day:02d}", f"{dd.month:02d}", f"{dd.day:02d}.{dd.month:02d}.{dd.year}"}
    allowed |= {str(n) for n in range(0, 13)}  # small counts ("2 weeks", "1 month")
    return allowed


def unsupported_numbers(text: str, allowed: set[str]) -> list[str]:
    tokens = _NUMBER.findall(text.translate(_EASTERN_DIGITS))
    bad = []
    for tok in tokens:
        pieces = [tok, tok.rstrip(".,")] + re.split(r"[.,]", tok)
        if not any(p in allowed for p in pieces if p):
            bad.append(tok)
    return bad


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


def explain(state: PipelineState, deps: PipelineDeps, language: str | None = None) -> PipelineState:
    assert state.facts is not None
    language = language or state.language
    lang = languages().get(language) or languages()["en"]
    passages = state.passages or []
    letter_type = state.classification.letter_type if state.classification else LetterType.OTHER
    vault = PiiVault()
    redacted = vault.redact_document(state.document)
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
            FakeProvider._explain(  # noqa: SLF001 - the template explainer is the fallback
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

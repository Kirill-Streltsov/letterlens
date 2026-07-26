"""Letter use cases for the reader (the client)."""

from __future__ import annotations

import logging
from typing import Any

from letterlens.api.errors import ApiError, bad_request, not_found
from letterlens.api.schemas import (
    CitationOut,
    CreateLetterRequest,
    CreateLetterResponse,
    DeadlineSummary,
    LetterListItem,
    LetterView,
    QuestionResponse,
    ShareInfo,
    dump,
)
from letterlens.container import Container
from letterlens.db import Conn
from letterlens.db import repo as R
from letterlens.domain import FactStatus, LetterStatus
from letterlens.i18n import REFUSAL, is_available, languages, localized
from letterlens.llm import Task
from letterlens.llm import prompts as P
from letterlens.llm.outputs import AnswerDraft, GuardDecision
from letterlens.llm.types import LLMError
from letterlens.observability import emit_metric
from letterlens.pipeline.state import PipelineState
from letterlens.pipeline.steps import _facts_for_prompt, allowed_numbers, unsupported_numbers
from letterlens.safety.guardrail import check_question_rules, is_advisory_output
from letterlens.safety.pii import PiiVault
from letterlens.services.principal import Principal

log = logging.getLogger(__name__)

FREE_MAX_RETENTION_DAYS = 30
OFF_TOPIC = {
    "en": "I can only answer questions about this letter.",
    "de": "Ich kann nur Fragen zu diesem Brief beantworten.",
}


def _require_language(code: str) -> None:
    if not is_available(code):
        raise bad_request("language_unavailable", f"language '{code}' is not available")


def next_deadline(state: PipelineState, language: str) -> DeadlineSummary | None:
    if state.facts is None:
        return None
    dated = [d for d in state.facts.deadlines if d.due_date is not None]
    if not dated:
        return None
    first = min(dated, key=lambda d: d.due_date)  # type: ignore[arg-type, return-value]
    labels = state.explanations.get(language) or next(iter(state.explanations.values()), None)
    label = (labels.deadline_labels.get(first.id) if labels else None) or first.description
    return DeadlineSummary(due_date=first.due_date, status=first.status.value, label=label)


def _explanation_language(state: PipelineState, requested: str) -> str | None:
    if requested in state.explanations:
        return requested
    if state.language in state.explanations:
        return state.language
    return next(iter(state.explanations), None)



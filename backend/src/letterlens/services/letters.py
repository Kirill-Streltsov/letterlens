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


class LetterService:
    def __init__(self, container: Container) -> None:
        self.c = container

    # -- create ---------------------------------------------------------------

    def create(
        self, principal: Principal, body: CreateLetterRequest, idempotency_key: str | None
    ) -> tuple[CreateLetterResponse, bool]:
        """Returns the response and whether the pipeline must be started."""
        _require_language(body.language)
        settings = self.c.settings
        plus = principal.plan == "plus"
        retention = body.retention_days if plus else min(body.retention_days, FREE_MAX_RETENTION_DAYS)
        with self.c.db.session(principal.ctx) as conn:
            if R.hit_rate_limit(conn, f"{principal.user_id}:letters", settings.rate_limit_per_minute):
                raise ApiError(429, "rate_limited", "too many requests, try again in a minute")
            if idempotency_key:
                previous = R.idempotent_response(conn, principal.user_id, idempotency_key)
                if previous is not None:
                    return CreateLetterResponse.model_validate(previous), False
            limit = None if plus else settings.free_letters_per_month
            if not R.consume_letter_quota(conn, principal.user_id, limit):
                raise ApiError(
                    402, "quota_exceeded", f"the free plan includes {limit} letters per month"
                )
            state = PipelineState(
                letter_id=R.new_id(),
                owner_id=principal.user_id,
                language=body.language,
                document=body.document,
            )
            expires = R.insert_letter(conn, self.c.keys, state, retention)
            R.audit(conn, principal.user_id, "letter.create", "letter", state.letter_id,
                    details={"lines": len(body.document.lines), "engine": body.document.ocr_engine})
            response = CreateLetterResponse(
                id=state.letter_id, status=LetterStatus.RECEIVED, expires_at=expires
            )
            if idempotency_key:
                R.store_idempotent_response(conn, principal.user_id, idempotency_key, dump(response))
        emit_metric("LettersCreated", 1)
        return response, True

    # -- read -----------------------------------------------------------------

    def _row_and_state(self, conn: Conn, letter_id: str) -> tuple[dict[str, Any], PipelineState]:
        row = R.letter_row(conn, letter_id)
        if row is None:
            raise not_found("letter")
        return row, R.load_state(conn, self.c.keys, row)

    def view(self, conn: Conn, letter_id: str, language: str, include_images: bool = True) -> LetterView:
        row, state = self._row_and_state(conn, letter_id)
        lang = _explanation_language(state, language)
        shares = [
            ShareInfo(
                id=s["id"],
                tenant_id=s["tenant_id"],
                tenant_name=s["tenant_name"],
                case_status=s["case_status"],
                expires_at=s["expires_at"],
                revoked=s["revoked_at"] is not None,
            )
            for s in R.shares_for_letter(conn, letter_id)
        ]
        images: list[str] = []
        if include_images and self.c.storage.enabled:
            images = [self.c.storage.download_url(k) for k in row["image_keys"]]
        return LetterView(
            id=row["id"],
            status=LetterStatus(row["status"]),
            error=row["error"],
            language=row["language"],
            created_at=row["created_at"],
            expires_at=row["expires_at"],
            lines=state.document.lines,
            classification=state.classification,
            facts=state.facts,
            explanation=state.explanations.get(lang) if lang else None,
            explanation_languages=sorted(state.explanations),
            degraded=state.degraded,
            degraded_reasons=state.degraded_reasons,
            image_urls=images,
            shares=shares,
        )

    def get(self, principal: Principal, letter_id: str, language: str) -> LetterView:
        with self.c.db.session(principal.ctx) as conn:
            return self.view(conn, letter_id, language)

    def list(self, principal: Principal) -> list[LetterListItem]:
        items = []
        with self.c.db.session(principal.ctx) as conn:
            for row in R.list_letters(conn, principal.user_id):
                state = R.load_state(conn, self.c.keys, row)
                lang = _explanation_language(state, row["language"])
                exp = state.explanations.get(lang) if lang else None
                items.append(
                    LetterListItem(
                        id=row["id"],
                        status=LetterStatus(row["status"]),
                        letter_type=row["letter_type"],
                        headline=exp.headline if exp else None,
                        sender=state.facts.sender.value if state.facts else None,
                        next_deadline=next_deadline(state, row["language"]),
                        created_at=row["created_at"],
                        expires_at=row["expires_at"],
                        shared=bool(R.shares_for_letter(conn, row["id"])),
                    )
                )
        return items

    # -- change ---------------------------------------------------------------

    def request_explanation(self, principal: Principal, letter_id: str, language: str) -> bool:
        """Returns True when a new explanation run must start."""
        _require_language(language)
        with self.c.db.session(principal.ctx) as conn:
            row, state = self._row_and_state(conn, letter_id)
            if row["owner_id"] != principal.user_id:
                raise not_found("letter")
            if row["status"] != LetterStatus.READY.value:
                raise ApiError(409, "not_ready", "the letter is still being processed")
            if language in state.explanations:
                return False
            R.set_letter_status(conn, letter_id, LetterStatus.PROCESSING, None)
        return True


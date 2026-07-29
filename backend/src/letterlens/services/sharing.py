"""Sharing a letter with a counselling service, case inbox and messages."""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from letterlens.api.errors import ApiError, bad_request, forbidden, not_found
from letterlens.api.schemas import (
    CONSENT_VERSION,
    CaseDetail,
    CaseItem,
    CounsellingService,
    InviteResponse,
    MessageOut,
    ShareInfo,
    ShareRequest,
    StatsRow,
)
from letterlens.container import Container
from letterlens.db import Conn
from letterlens.db import repo as R
from letterlens.i18n import is_available, languages
from letterlens.llm import Task
from letterlens.llm import prompts as P
from letterlens.llm.outputs import ReplyTranslation
from letterlens.llm.types import LLMError
from letterlens.services.letters import LetterService, next_deadline
from letterlens.services.principal import Principal

COUNSELLOR_LANGUAGE = "de"
_INVITE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class SharingService:
    def __init__(self, container: Container, letters: LetterService) -> None:
        self.c = container
        self.letters = letters

    # -- client side ----------------------------------------------------------

    def services(self, principal: Principal, city: str | None) -> list[CounsellingService]:
        with self.c.db.session(principal.ctx) as conn:
            return [CounsellingService(**row) for row in R.counselling_services(conn, city)]

    def share(self, principal: Principal, letter_id: str, body: ShareRequest) -> tuple[ShareInfo, bool]:
        """Returns the share and whether a German explanation must be generated."""
        if body.consent_text_version != CONSENT_VERSION:
            raise bad_request("consent_outdated", "please accept the current consent text")
        with self.c.db.session(principal.ctx) as conn:
            row = R.letter_row(conn, letter_id)
            if row is None or row["owner_id"] != principal.user_id:
                raise not_found("letter")
            if not any(s["id"] == body.tenant_id for s in R.counselling_services(conn, None)):
                raise not_found("counselling service")
            share = R.create_share(
                conn, letter_id, principal.user_id, body.tenant_id, body.consent_text_version,
                body.days, row["language"],
            )
            R.audit(conn, principal.user_id, "share.create", "share", share["id"],
                    tenant_id=body.tenant_id, details={"letter_id": letter_id, "days": body.days,
                                                       "consent": body.consent_text_version})
            state = R.load_state(conn, self.c.keys, row)
            needs_german = COUNSELLOR_LANGUAGE not in state.explanations and row["status"] == "ready"
            tenant_name = next(s["tenant_name"] for s in R.shares_for_letter(conn, letter_id)
                               if s["id"] == share["id"])
        info = ShareInfo(
            id=share["id"], tenant_id=share["tenant_id"], tenant_name=tenant_name,
            case_status=share["case_status"], expires_at=share["expires_at"], revoked=False,
        )
        return info, needs_german

    def revoke(self, principal: Principal, share_id: str) -> None:
        with self.c.db.session(principal.ctx) as conn:
            share = R.get_share(conn, share_id)
            if share is None or share["owner_id"] != principal.user_id:
                raise not_found("share")
            R.revoke_share(conn, share_id)
            R.audit(conn, principal.user_id, "share.revoke", "share", share_id,
                    tenant_id=share["tenant_id"])

    # -- messages -------------------------------------------------------------

    def _translate(self, principal: Principal, text: str, language: str) -> str:
        lang = languages().get(language) or languages()["en"]
        try:
            result = self.c.gateway.generate(
                Task.TRANSLATE_REPLY,
                ReplyTranslation,
                P.TRANSLATE_REPLY_SYSTEM_TEMPLATE.format(language_name=lang.name),
                f"<message>\n{text}\n</message>",
                P.TRANSLATE_REPLY_VERSION,
                context={"text": text, "language": language},
                user_id=principal.user_id,
                max_tokens=2000,
            )
        except LLMError as exc:
            raise ApiError(503, "llm_unavailable", "translation is not available right now") from exc
        return result.translation


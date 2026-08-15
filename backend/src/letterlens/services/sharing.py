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
                conn,
                letter_id,
                principal.user_id,
                body.tenant_id,
                body.consent_text_version,
                body.days,
                row["language"],
            )
            R.audit(
                conn,
                principal.user_id,
                "share.create",
                "share",
                share["id"],
                tenant_id=body.tenant_id,
                details={"letter_id": letter_id, "days": body.days, "consent": body.consent_text_version},
            )
            state = R.load_state(conn, self.c.keys, row)
            needs_german = COUNSELLOR_LANGUAGE not in state.explanations and row["status"] == "ready"
            tenant_name = next(
                s["tenant_name"] for s in R.shares_for_letter(conn, letter_id) if s["id"] == share["id"]
            )
        info = ShareInfo(
            id=share["id"],
            tenant_id=share["tenant_id"],
            tenant_name=tenant_name,
            case_status=share["case_status"],
            expires_at=share["expires_at"],
            revoked=False,
        )
        return info, needs_german

    def revoke(self, principal: Principal, share_id: str) -> None:
        with self.c.db.session(principal.ctx) as conn:
            share = R.get_share(conn, share_id)
            if share is None or share["owner_id"] != principal.user_id:
                raise not_found("share")
            R.revoke_share(conn, share_id)
            R.audit(conn, principal.user_id, "share.revoke", "share", share_id, tenant_id=share["tenant_id"])

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

    def _share_for(self, conn: Conn, principal: Principal, share_id: str) -> tuple[dict[str, Any], str]:
        share = R.get_share(conn, share_id)
        if share is None:
            raise not_found("share")
        if share["owner_id"] == principal.user_id:
            return share, "client"
        if share["tenant_id"] in principal.counselling_tenant_ids:
            return share, "counsellor"
        raise not_found("share")

    def messages(self, principal: Principal, share_id: str) -> list[MessageOut]:
        with self.c.db.session(principal.ctx) as conn:
            share, role = self._share_for(conn, principal, share_id)
            rows = R.list_messages(conn, self.c.keys, share)
        reader_language = share["client_language"] if role == "client" else COUNSELLOR_LANGUAGE
        out = []
        for r in rows:
            body = json.loads(r["body"])
            translated = body["translations"].get(reader_language)
            out.append(
                MessageOut(
                    id=r["id"],
                    author_role=r["author_role"],
                    created_at=r["created_at"],
                    text=translated or body["text"],
                    original_text=body["text"] if translated else None,
                )
            )
        return out

    def post_message(self, principal: Principal, share_id: str, text: str) -> MessageOut:
        with self.c.db.session(principal.ctx) as conn:
            share, role = self._share_for(conn, principal, share_id)
            if share["revoked_at"] is not None:
                raise ApiError(409, "share_revoked", "this share was revoked")
        source = share["client_language"] if role == "client" else COUNSELLOR_LANGUAGE
        target = COUNSELLOR_LANGUAGE if role == "client" else share["client_language"]
        translations = {source: text}
        if target != source:
            translations[target] = self._translate(principal, text, target)
        body = json.dumps({"text": text, "language": source, "translations": translations}).encode()
        with self.c.db.session(principal.ctx) as conn:
            row = R.insert_message(conn, self.c.keys, share, principal.user_id, role, body)
            R.audit(
                conn,
                principal.user_id,
                "message.create",
                "share",
                share_id,
                tenant_id=share["tenant_id"],
                details={"role": role},
            )
        return MessageOut(
            id=row["id"],
            author_role=role,
            text=text,
            original_text=None,
            created_at=row["created_at"],
        )

    # -- counsellor side --------------------------------------------------------

    def _require_counsellor(self, principal: Principal) -> None:
        if not principal.counselling_tenant_ids:
            raise forbidden("counsellor access only")

    def cases(self, principal: Principal, status: str | None) -> list[CaseItem]:
        self._require_counsellor(principal)
        items = []
        with self.c.db.session(principal.ctx) as conn:
            for row in R.tenant_cases(conn, list(principal.counselling_tenant_ids), status):
                letter = R.letter_row(conn, row["letter_id"])
                if letter is None:
                    continue
                state = R.load_state(conn, self.c.keys, letter)
                exp = state.explanations.get(COUNSELLOR_LANGUAGE) or state.explanations.get(state.language)
                items.append(
                    CaseItem(
                        share_id=row["id"],
                        letter_id=row["letter_id"],
                        tenant_id=row["tenant_id"],
                        client_name=row["client_name"],
                        client_language=row["client_language"],
                        letter_type=row["letter_type"],
                        letter_status=row["letter_status"],
                        case_status=row["case_status"],
                        assigned_to=row["assigned_to"],
                        headline=exp.headline if exp else None,
                        next_deadline=next_deadline(state, COUNSELLOR_LANGUAGE),
                        created_at=row["created_at"],
                        expires_at=row["expires_at"],
                    )
                )
        return items

    def case(self, principal: Principal, share_id: str) -> CaseDetail:
        self._require_counsellor(principal)
        with self.c.db.session(principal.ctx) as conn:
            share = R.get_share(conn, share_id)
            if share is None or share["tenant_id"] not in principal.counselling_tenant_ids:
                raise not_found("case")
            view = self.letters.view(conn, share["letter_id"], share["client_language"])
            client = R.get_user(conn, share["owner_id"])
            R.audit(conn, principal.user_id, "case.view", "share", share_id, tenant_id=share["tenant_id"])
            row = R.letter_row(conn, share["letter_id"])
            assert row is not None
            state = R.load_state(conn, self.c.keys, row)
        return CaseDetail(
            share_id=share_id,
            case_status=share["case_status"],
            client_name=client["display_name"] if client else None,
            client_language=share["client_language"],
            letter=view,
            explanation_de=state.explanations.get(COUNSELLOR_LANGUAGE),
        )

    def update_case(
        self, principal: Principal, share_id: str, case_status: str | None, assigned_to: str | None
    ) -> None:
        self._require_counsellor(principal)
        with self.c.db.session(principal.ctx) as conn:
            share = R.get_share(conn, share_id)
            if share is None or share["tenant_id"] not in principal.counselling_tenant_ids:
                raise not_found("case")
            R.update_case(conn, share_id, case_status, assigned_to)
            R.audit(
                conn,
                principal.user_id,
                "case.update",
                "share",
                share_id,
                tenant_id=share["tenant_id"],
                details={"case_status": case_status},
            )

    def translate(self, principal: Principal, text: str, language: str) -> str:
        self._require_counsellor(principal)
        if not is_available(language):
            raise bad_request("language_unavailable", f"language '{language}' is not available")
        return self._translate(principal, text, language)

    def stats(self, principal: Principal, tenant_id: str, months: int) -> list[StatsRow]:
        if tenant_id not in principal.counselling_tenant_ids:
            raise not_found("tenant")
        since = datetime.now(UTC) - timedelta(days=31 * months)
        with self.c.db.session(principal.ctx) as conn:
            return [StatsRow(**r) for r in R.tenant_stats(conn, tenant_id, since)]

    def invite(self, principal: Principal, tenant_id: str, role: str) -> InviteResponse:
        if not principal.is_tenant_admin(tenant_id):
            raise forbidden("tenant admins only")
        code = "-".join("".join(secrets.choice(_INVITE_ALPHABET) for _ in range(4)) for _ in range(3))
        with self.c.db.session(principal.ctx) as conn:
            R.create_invite(conn, tenant_id, role, principal.user_id, code)
            R.audit(
                conn,
                principal.user_id,
                "invite.create",
                "tenant",
                tenant_id,
                tenant_id=tenant_id,
                details={"role": role},
            )
        return InviteResponse(code=code, expires_in_days=14)

    def redeem(self, principal: Principal, code: str) -> None:
        from letterlens.db import DbContext

        with self.c.db.session(DbContext.as_system()) as conn:
            result = R.redeem_invite(conn, code, principal.user_id)
            if result is None:
                raise not_found("invite")
            R.audit(
                conn,
                principal.user_id,
                "invite.redeem",
                "tenant",
                result["tenant_id"],
                tenant_id=result["tenant_id"],
                details={"role": result["role"]},
            )

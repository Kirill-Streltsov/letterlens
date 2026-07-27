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


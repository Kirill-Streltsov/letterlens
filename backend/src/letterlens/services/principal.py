"""The authenticated caller and the database context derived from it."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from letterlens.api.auth import Identity
from letterlens.db import Database, DbContext
from letterlens.db.repo import Membership, memberships, resolve_user

PLATFORM_ADMIN_GROUP = "platform_admin"
_CACHE_SECONDS = 60


@dataclass(frozen=True)
class Principal:
    identity: Identity
    user: dict[str, Any]
    memberships: tuple[Membership, ...]

    @property
    def user_id(self) -> str:
        return str(self.user["id"])


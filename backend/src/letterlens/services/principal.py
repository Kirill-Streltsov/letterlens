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

    @property
    def counselling_tenant_ids(self) -> tuple[str, ...]:
        """Tenants whose shared letters this user may read. Employees get none."""
        return tuple(
            m.tenant_id
            for m in self.memberships
            if m.kind == "counselling" and m.role in {"counsellor", "admin"}
        )

    def is_tenant_admin(self, tenant_id: str) -> bool:
        return any(m.tenant_id == tenant_id and m.role == "admin" for m in self.memberships)

    @property
    def is_platform_admin(self) -> bool:
        return PLATFORM_ADMIN_GROUP in self.identity.groups

    @property
    def plan(self) -> str:
        expires = self.user.get("plan_expires_at")
        if self.user["plan"] == "plus" and (expires is None or expires > datetime.now(UTC)):
            return "plus"
        if any(m.kind == "employer" for m in self.memberships):
            return "plus"  # employer benefit
        return "free"

    @property
    def ctx(self) -> DbContext:
        return DbContext(user_id=self.user_id, tenant_ids=self.counselling_tenant_ids)


class PrincipalResolver:
    """Maps a token subject to a user row and memberships, with a short cache."""

    def __init__(self, db: Database) -> None:
        self.db = db
        self._cache: dict[str, tuple[float, Principal]] = {}

    def resolve(self, identity: Identity) -> Principal:
        hit = self._cache.get(identity.sub)
        if hit and hit[0] > time.monotonic() and hit[1].identity == identity:
            return hit[1]
        with self.db.session(DbContext.as_system()) as conn:
            user = resolve_user(conn, identity.sub)
            members = tuple(memberships(conn, str(user["id"])))
        principal = Principal(identity, user, members)
        self._cache[identity.sub] = (time.monotonic() + _CACHE_SECONDS, principal)
        return principal

    def invalidate(self, sub: str) -> None:
        self._cache.pop(sub, None)

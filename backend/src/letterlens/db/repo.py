"""SQL repositories. Every function takes a connection from Database.session().

RLS decides which rows a function can see. Functions do not filter by owner
for security; they filter by owner only where the query needs it.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from psycopg.types.json import Jsonb

from letterlens.crypto import DekCache, Kek, decrypt, encrypt, new_dek
from letterlens.db import Conn, Database, DbContext
from letterlens.domain import LetterStatus
from letterlens.llm.types import LLMCall
from letterlens.pipeline.state import PipelineState


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Users and memberships
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Membership:
    tenant_id: str
    role: str
    kind: str
    name: str


def resolve_user(conn: Conn, cognito_sub: str) -> dict[str, Any]:
    """Find or create the user for a token subject. Needs the system context."""
    conn.execute(
        "INSERT INTO users (cognito_sub) VALUES (%s) ON CONFLICT (cognito_sub) DO NOTHING",
        (cognito_sub,),
    )
    row = conn.execute("SELECT * FROM users WHERE cognito_sub = %s", (cognito_sub,)).fetchone()
    assert row is not None
    return row


def memberships(conn: Conn, user_id: str) -> list[Membership]:
    rows = conn.execute(
        "SELECT m.tenant_id::text, m.role, t.kind, t.name FROM memberships m"
        " JOIN tenants t ON t.id = m.tenant_id WHERE m.user_id = %s",
        (user_id,),
    ).fetchall()
    return [Membership(r["tenant_id"], r["role"], r["kind"], r["name"]) for r in rows]


def get_user(conn: Conn, user_id: str) -> dict[str, Any] | None:
    return conn.execute("SELECT * FROM users WHERE id = %s", (user_id,)).fetchone()


def update_user(conn: Conn, user_id: str, **fields: Any) -> None:
    allowed = {"display_name", "preferred_language", "plan", "plan_source", "plan_expires_at",
               "stripe_customer_id"}
    sets = {k: v for k, v in fields.items() if k in allowed}
    if not sets:
        return
    assignments = ", ".join(f"{k} = %({k})s" for k in sets)
    conn.execute(f"UPDATE users SET {assignments} WHERE id = %(id)s", {**sets, "id": user_id})  # noqa: S608 - keys are allow-listed


def delete_user(conn: Conn, user_id: str) -> list[str]:
    """Delete the user and everything they own. Returns S3 keys to delete."""
    rows = conn.execute("SELECT image_keys FROM letters WHERE owner_id = %s", (user_id,)).fetchall()
    keys = [k for r in rows for k in r["image_keys"]]
    conn.execute("DELETE FROM users WHERE id = %s", (user_id,))
    return keys


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


class KeyRing:
    """Unwraps per-user DEKs with the KEK and caches them briefly."""

    def __init__(self, kek: Kek, cache: DekCache | None = None) -> None:
        self.kek = kek
        self.cache = cache or DekCache()


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

    def dek_for(self, conn: Conn, user_id: str, create: bool = False) -> bytes:
        cached = self.cache.get(user_id)
        if cached is not None:
            return cached
        row = conn.execute(
            "SELECT wrapped_dek FROM user_keys WHERE user_id = %s", (user_id,)
        ).fetchone()
        if row is None:
            if not create:
                raise LookupError("no data key for this user")
            dek = new_dek()
            conn.execute(
                "INSERT INTO user_keys (user_id, wrapped_dek, kek_version) VALUES (%s, %s, %s)"
                " ON CONFLICT (user_id) DO NOTHING",
                (user_id, self.kek.wrap(dek, user_id), self.kek.version),
            )
            # Another request may have created the key first; read the stored one.
            stored = conn.execute(
                "SELECT wrapped_dek FROM user_keys WHERE user_id = %s", (user_id,)
            ).fetchone()
            assert stored is not None
            dek = self.kek.unwrap(bytes(stored["wrapped_dek"]), user_id)
        else:
            dek = self.kek.unwrap(bytes(row["wrapped_dek"]), user_id)
        self.cache.put(user_id, dek)
        return dek

    def seal(self, conn: Conn, owner_id: str, record_id: str, plaintext: bytes) -> bytes:
        return encrypt(self.dek_for(conn, owner_id, create=True), plaintext, record_id)

    def open(self, conn: Conn, owner_id: str, record_id: str, blob: bytes) -> bytes:
        return decrypt(self.dek_for(conn, owner_id), bytes(blob), record_id)


# ---------------------------------------------------------------------------
# Letters
# ---------------------------------------------------------------------------


def insert_letter(
    conn: Conn, keys: KeyRing, state: PipelineState, retention_days: int
) -> datetime:
    expires = utcnow() + timedelta(days=retention_days)
    blob = keys.seal(conn, state.owner_id, state.letter_id, state.model_dump_json().encode())
    conn.execute(
        "INSERT INTO letters (id, owner_id, status, language, state, expires_at)"
        " VALUES (%s, %s, 'received', %s, %s, %s)",
        (state.letter_id, state.owner_id, state.language, blob, expires),
    )
    return expires


def letter_row(conn: Conn, letter_id: str) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT id::text, owner_id::text, status, letter_type, language, state, image_keys,"
        " degraded, error, created_at, updated_at, expires_at FROM letters WHERE id = %s",
        (letter_id,),
    ).fetchone()


def load_state(conn: Conn, keys: KeyRing, row: dict[str, Any]) -> PipelineState:
    raw = keys.open(conn, row["owner_id"], row["id"], row["state"])
    return PipelineState.model_validate_json(raw)


def save_state(conn: Conn, keys: KeyRing, state: PipelineState) -> None:
    blob = keys.seal(conn, state.owner_id, state.letter_id, state.model_dump_json().encode())
    letter_type = state.classification.letter_type.value if state.classification else None
    conn.execute(
        "UPDATE letters SET state = %s, letter_type = coalesce(%s, letter_type), degraded = %s,"
        " updated_at = now() WHERE id = %s",
        (blob, letter_type, state.degraded, state.letter_id),
    )


def set_letter_status(conn: Conn, letter_id: str, status: LetterStatus, error: str | None) -> None:
    conn.execute(
        "UPDATE letters SET status = %s, error = %s, updated_at = now() WHERE id = %s",
        (status.value, error, letter_id),
    )


def list_letters(conn: Conn, owner_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return conn.execute(
        "SELECT id::text, owner_id::text, status, letter_type, language, state, image_keys,"
        " degraded, error, created_at, updated_at, expires_at FROM letters"
        " WHERE owner_id = %s ORDER BY created_at DESC LIMIT %s",
        (owner_id, limit),
    ).fetchall()


def set_retention(conn: Conn, letter_id: str, days: int) -> datetime | None:
    row = conn.execute(
        "UPDATE letters SET expires_at = created_at + make_interval(days => %s)"
        " WHERE id = %s RETURNING expires_at",
        (days, letter_id),
    ).fetchone()
    return row["expires_at"] if row else None


def add_image_keys(conn: Conn, letter_id: str, keys: list[str]) -> None:
    conn.execute(
        "UPDATE letters SET image_keys = image_keys || %s::text[] WHERE id = %s",
        (keys, letter_id),
    )


def delete_letter(conn: Conn, letter_id: str) -> list[str] | None:
    row = conn.execute(
        "DELETE FROM letters WHERE id = %s RETURNING image_keys", (letter_id,)
    ).fetchone()
    return list(row["image_keys"]) if row else None


def purge_expired(conn: Conn, limit: int = 500) -> tuple[int, list[str]]:
    rows = conn.execute(
        "DELETE FROM letters WHERE id IN ("
        " SELECT id FROM letters WHERE expires_at < now() ORDER BY expires_at LIMIT %s)"
        " RETURNING image_keys",
        (limit,),
    ).fetchall()
    conn.execute("DELETE FROM shares WHERE expires_at < now() - interval '30 days'")
    conn.execute("DELETE FROM rate_limits WHERE window_start < now() - interval '1 day'")
    conn.execute("DELETE FROM idempotency_keys WHERE created_at < now() - interval '2 days'")
    return len(rows), [k for r in rows for k in r["image_keys"]]



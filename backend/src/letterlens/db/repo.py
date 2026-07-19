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



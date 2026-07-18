"""Database access with a row-level-security context per transaction."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

Conn = Connection[dict[str, Any]]


@dataclass(frozen=True)
class DbContext:
    """Who the current transaction runs for. RLS policies read these values."""

    user_id: str | None = None
    tenant_ids: tuple[str, ...] = ()
    system: bool = False

    @classmethod
    def as_system(cls) -> DbContext:
        return cls(system=True)


class Database:
    def __init__(self, url: str, max_size: int = 4) -> None:
        # prepare_threshold=None: Neon's pooler (PgBouncer, transaction mode) does not
        # support server-side prepared statements across transactions.
        self.pool: ConnectionPool[Conn] = ConnectionPool(
            url,
            min_size=1,
            max_size=max_size,
            kwargs={"prepare_threshold": None, "row_factory": dict_row, "autocommit": False},
            check=ConnectionPool.check_connection,
            open=False,
        )
        self._opened = False


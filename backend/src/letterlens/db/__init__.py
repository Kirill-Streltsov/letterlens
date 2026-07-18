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

    def open(self) -> None:
        if not self._opened:
            self.pool.open(wait=True, timeout=15)
            self._opened = True

    def close(self) -> None:
        if self._opened:
            self.pool.close()
            self._opened = False

    @contextmanager
    def session(self, ctx: DbContext) -> Iterator[Conn]:
        self.open()
        with self.pool.connection() as conn, conn.transaction():
            conn.execute(
                "SELECT set_config('app.user_id', %s, true),"
                " set_config('app.tenant_ids', %s, true),"
                " set_config('app.system', %s, true)",
                (ctx.user_id or "", ",".join(ctx.tenant_ids), "on" if ctx.system else ""),
            )
            yield conn

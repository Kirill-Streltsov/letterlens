"""Apply SQL migrations in order. Run with the owner role, never with the app role.

Usage:
  LETTERLENS_DATABASE_ADMIN_URL=postgresql://owner@host/db \
  LETTERLENS_DB_APP_PASSWORD=... python -m letterlens.db.migrate
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg
from psycopg import sql

MIGRATIONS = Path(__file__).resolve().parents[3] / "migrations"


def migrate(admin_url: str, app_password: str | None = None, directory: Path = MIGRATIONS) -> list[str]:
    applied: list[str] = []
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            " version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now())"
        )
        done = {row[0] for row in conn.execute("SELECT version FROM schema_migrations")}
        for path in sorted(directory.glob("*.sql")):
            if path.stem in done:
                continue
            with conn.transaction():
                conn.execute(path.read_text(encoding="utf-8"))  # type: ignore[arg-type]
                conn.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.stem,))
            applied.append(path.stem)
        if app_password:
            conn.execute(
                sql.SQL("ALTER ROLE letterlens_app LOGIN PASSWORD {}").format(
                    sql.Literal(app_password)
                )
            )
    return applied


def main() -> None:
    admin_url = os.environ.get("LETTERLENS_DATABASE_ADMIN_URL")
    if not admin_url:
        sys.exit("LETTERLENS_DATABASE_ADMIN_URL is not set")
    applied = migrate(admin_url, os.environ.get("LETTERLENS_DB_APP_PASSWORD"))
    print(f"applied: {applied or 'nothing'}")  # noqa: T201


if __name__ == "__main__":
    main()

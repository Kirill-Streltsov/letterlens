"""Shared fixtures.

Database tests need a PostgreSQL server. Set LETTERLENS_TEST_ADMIN_URL to an
owner connection (default: the docker-compose service). The fixture creates a
fresh database per test session, applies migrations and connects as the
non-owner role letterlens_app, so RLS is active exactly as in production.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest

from letterlens.config import Settings
from letterlens.db import Database, DbContext
from letterlens.db.migrate import migrate

DEFAULT_ADMIN = "postgresql://letterlens_owner:letterlens_owner@localhost:5433/letterlens"
APP_PASSWORD = "letterlens_app_test"


def _with_db(url: str, dbname: str, user: str | None = None, password: str | None = None) -> str:
    parts = urlparse(url)
    netloc = parts.netloc
    if user:
        host = netloc.split("@")[-1]
        netloc = f"{user}:{password}@{host}"
    return urlunparse(parts._replace(path=f"/{dbname}", netloc=netloc))


@pytest.fixture(scope="session")
def admin_url() -> str:
    return os.environ.get("LETTERLENS_TEST_ADMIN_URL", DEFAULT_ADMIN)


@pytest.fixture(scope="session")
def database_urls(admin_url: str) -> Iterator[tuple[str, str]]:
    try:
        with psycopg.connect(admin_url, autocommit=True, connect_timeout=3) as conn:
            name = f"letterlens_test_{uuid.uuid4().hex[:8]}"
            conn.execute(f'CREATE DATABASE "{name}"')
    except psycopg.OperationalError:
        pytest.skip("PostgreSQL is not available (start it with: docker compose up -d)")
    test_admin = _with_db(admin_url, name)
    migrate(test_admin, APP_PASSWORD)
    app_url = _with_db(admin_url, name, "letterlens_app", APP_PASSWORD)
    yield test_admin, app_url
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture(scope="session")
def db(database_urls: tuple[str, str]) -> Iterator[Database]:
    database = Database(database_urls[1])
    yield database
    database.close()


@pytest.fixture
def settings(database_urls: tuple[str, str]) -> Settings:
    return Settings(env="test", database_url=database_urls[1], llm_provider="fake")


@pytest.fixture
def system(db: Database) -> Iterator[psycopg.Connection]:  # type: ignore[type-arg]
    with db.session(DbContext.as_system()) as conn:
        yield conn

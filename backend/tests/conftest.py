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



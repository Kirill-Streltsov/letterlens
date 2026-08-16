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


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



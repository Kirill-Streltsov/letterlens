"""Seed a local database with a demo counselling service, a counsellor and demo letters.

Run after migrations: uv run python scripts/seed_demo.py
Sign in on the web app (local mode) as "demo-client" or "counsellor-anna".
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from evals.handwritten import HANDWRITTEN
from letterlens.api.app import create_app
from letterlens.config import Settings
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.synthetic import generate_corpus, to_document

CLIENT = {"X-Dev-User": "demo-client"}



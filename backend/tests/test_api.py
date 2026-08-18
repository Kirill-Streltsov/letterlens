"""API integration tests: HTTP -> services -> PostgreSQL (RLS on) -> offline pipeline."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from letterlens.api.app import create_app
from letterlens.config import Settings
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.synthetic import generate_corpus, to_document

pytestmark = pytest.mark.db
WEBHOOK_SECRET = "whsec_test_secret"


@pytest.fixture
def client(database_urls: tuple[str, str]) -> Iterator[TestClient]:
    settings = Settings(
        env="test",
        database_url=database_urls[1],
        llm_provider="fake",
        stripe_webhook_secret=WEBHOOK_SECRET,
        free_letters_per_month=3,
    )
    app = create_app(settings)
    with TestClient(app) as test_client:
        yield test_client
    app.state.services.container.db.close()


def user() -> dict[str, str]:
    return {"X-Dev-User": f"u-{uuid.uuid4().hex[:8]}"}


def letter_body(n: int = 0, language: str = "en") -> dict[str, object]:
    doc = to_document(generate_corpus(1)[n]).model_dump(mode="json")
    return {"document": doc, "language": language}


def create(client: TestClient, headers: dict[str, str], n: int = 0) -> str:
    r = client.post("/v1/letters", json=letter_body(n), headers=headers)
    assert r.status_code == 202, r.text
    return str(r.json()["id"])



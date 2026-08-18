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


def test_requires_auth(client: TestClient) -> None:
    r = client.get("/v1/me")
    assert r.status_code == 401 and r.json()["code"] == "unauthorized"


def test_letter_lifecycle(client: TestClient) -> None:
    h = user()
    lid = create(client, h)
    view = client.get(f"/v1/letters/{lid}", headers=h).json()
    assert view["status"] == "ready"
    assert view["classification"]["letter_type"] == "tax"
    assert {d["status"] for d in view["facts"]["deadlines"]} == {"verified", "needs_check"}
    assert view["explanation"]["citations"]
    assert client.get("/v1/letters", headers=h).json()[0]["id"] == lid
    assert client.delete(f"/v1/letters/{lid}", headers=h).status_code == 204
    assert client.get(f"/v1/letters/{lid}", headers=h).status_code == 404


def test_other_users_get_404(client: TestClient) -> None:
    lid = create(client, user())
    intruder = user()
    assert client.get(f"/v1/letters/{lid}", headers=intruder).status_code == 404
    assert client.delete(f"/v1/letters/{lid}", headers=intruder).status_code == 404
    q = {"question": "What is this?", "language": "en"}
    assert client.post(f"/v1/letters/{lid}/questions", json=q, headers=intruder).status_code == 404


def test_idempotency_key(client: TestClient) -> None:
    h = {**user(), "Idempotency-Key": "abc-1"}
    a = client.post("/v1/letters", json=letter_body(), headers=h).json()
    b = client.post("/v1/letters", json=letter_body(), headers=h).json()
    assert a["id"] == b["id"]
    me = client.get("/v1/me", headers=h).json()
    assert me["letters_this_month"] == 1


def test_free_quota(client: TestClient) -> None:
    h = user()
    for _ in range(3):
        create(client, h)
    r = client.post("/v1/letters", json=letter_body(), headers=h)
    assert r.status_code == 402 and r.json()["code"] == "quota_exceeded"


def test_unknown_language_is_rejected(client: TestClient) -> None:
    r = client.post("/v1/letters", json=letter_body(language="xx"), headers=user())
    assert r.status_code == 400 and r.json()["code"] == "language_unavailable"



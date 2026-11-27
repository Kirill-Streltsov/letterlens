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


def test_validation_error_does_not_echo_input(client: TestClient) -> None:
    body = letter_body()
    body["document"]["lines"][0]["page"] = "SECRET-TEXT"  # type: ignore[index]
    r = client.post("/v1/letters", json=body, headers=user())
    assert r.status_code == 422 and "SECRET-TEXT" not in r.text


def test_question_guardrail(client: TestClient) -> None:
    h = user()
    lid = create(client, h)
    advice = client.post(
        f"/v1/letters/{lid}/questions",
        json={"question": "Sollte ich Einspruch einlegen?", "language": "de"},
        headers=h,
    ).json()
    assert advice["refused"] and advice["reason"] == "legal_advice" and advice["handover_suggested"]
    assert "Beratung" in advice["answer"]
    info = client.post(
        f"/v1/letters/{lid}/questions",
        json={"question": "What does Einspruch mean?", "language": "en"},
        headers=h,
    ).json()
    assert not info["refused"] and info["citations"]


def test_second_language(client: TestClient) -> None:
    h = user()
    lid = create(client, h)
    r = client.post(f"/v1/letters/{lid}/explanations", json={"language": "de"}, headers=h)
    assert r.status_code == 202 and r.json() == {"started": True}
    view = client.get(f"/v1/letters/{lid}?lang=de", headers=h).json()
    assert view["explanation"]["language"] == "de"
    assert set(view["explanation_languages"]) == {"en", "de"}


def test_sharing_flow(client: TestClient) -> None:
    services = client.app.state.services  # type: ignore[attr-defined]
    counsellor, other_counsellor = user(), user()
    with services.container.db.session(DbContext.as_system()) as conn:
        tenant = R.create_tenant(
            conn, f"Service {uuid.uuid4().hex[:4]}", "counselling", "Bochum", ["de"], True
        )
        other = R.create_tenant(conn, f"Other {uuid.uuid4().hex[:4]}", "counselling", "Essen", ["de"], True)
        R.add_member(
            conn, tenant, str(R.resolve_user(conn, "dev:" + counsellor["X-Dev-User"])["id"]), "admin"
        )
        R.add_member(
            conn,
            other,
            str(R.resolve_user(conn, "dev:" + other_counsellor["X-Dev-User"])["id"]),
            "counsellor",
        )

    h = user()
    lid = create(client, h)
    bad = {"tenant_id": tenant, "consent": False, "consent_text_version": "share-consent-v1"}
    assert client.post(f"/v1/letters/{lid}/shares", json=bad, headers=h).status_code == 422
    body = {"tenant_id": tenant, "consent": True, "consent_text_version": "share-consent-v1"}
    share = client.post(f"/v1/letters/{lid}/shares", json=body, headers=h).json()

    cases = client.get("/v1/counsellor/cases", headers=counsellor).json()
    assert [c["share_id"] for c in cases] == [share["id"]]
    assert client.get("/v1/counsellor/cases", headers=other_counsellor).json() == []
    assert client.get(f"/v1/counsellor/cases/{share['id']}", headers=other_counsellor).status_code == 404

    detail = client.get(f"/v1/counsellor/cases/{share['id']}", headers=counsellor).json()
    assert detail["explanation_de"] is not None  # German summary prepared on share

    sent = client.post(
        f"/v1/shares/{share['id']}/messages", json={"text": "Bitte Termin vereinbaren."}, headers=counsellor
    )
    assert sent.status_code == 201
    seen = client.get(f"/v1/shares/{share['id']}/messages", headers=h).json()
    assert seen[0]["original_text"] == "Bitte Termin vereinbaren."

    assert (
        client.patch(
            f"/v1/counsellor/cases/{share['id']}", json={"case_status": "closed"}, headers=counsellor
        ).status_code
        == 204
    )
    stats = client.get(f"/v1/counsellor/tenants/{tenant}/stats", headers=counsellor).json()
    assert stats[0]["closed"] == 1

    invite = client.post("/v1/counsellor/invites", json={"tenant_id": tenant}, headers=counsellor).json()
    newbie = user()
    assert client.post("/v1/invites/redeem", json={"code": invite["code"]}, headers=newbie).status_code == 204
    assert len(client.get("/v1/counsellor/cases", headers=newbie).json()) == 1
    assert client.post("/v1/invites/redeem", json={"code": invite["code"]}, headers=user()).status_code == 404

    assert client.delete(f"/v1/shares/{share['id']}", headers=h).status_code == 204
    assert client.get("/v1/counsellor/cases", headers=counsellor).json() == []


def test_account_deletion_crypto_shreds(client: TestClient) -> None:
    h = user()
    lid = create(client, h)
    assert client.get("/v1/me/export", headers=h).json()["letters"][0]["id"] == lid
    assert client.delete("/v1/me", headers=h).status_code == 204
    services = client.app.state.services  # type: ignore[attr-defined]
    with services.container.db.session(DbContext.as_system()) as conn:
        assert R.letter_row(conn, lid) is None
    # The sign-in account (email, password hash) is removed too.
    assert services.container.directory.deleted == [f"dev:{h['X-Dev-User']}"]


def test_cost_endpoint(client: TestClient) -> None:
    h = user()
    lid = create(client, h)
    cost = client.get(f"/v1/admin/letters/{lid}/cost", headers=h).json()
    assert cost["calls"] >= 2 and cost["input_tokens"] > 0
    assert client.get("/v1/admin/costs", headers=h).status_code == 403
    admin = {**user(), "X-Dev-Groups": "platform_admin"}
    assert client.get("/v1/admin/costs", headers=admin).status_code == 200


def stripe_signature(payload: bytes, secret: str) -> str:
    ts = int(time.time())
    mac = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={mac}"


def test_stripe_webhook_upgrades_plan_once(client: TestClient) -> None:
    h = user()
    me = client.get("/v1/me", headers=h).json()
    event = {
        "id": f"evt_{uuid.uuid4().hex}",
        "object": "event",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_1",
                "object": "subscription",
                "status": "active",
                "customer": "cus_1",
                "current_period_end": int(time.time()) + 86400 * 30,
                "metadata": {"kind": "plus", "user_id": me["id"]},
                "items": {"data": [{"quantity": 1}]},
            }
        },
    }
    payload = json.dumps(event).encode()
    bad = client.post(
        "/v1/billing/stripe/webhook", content=payload, headers={"Stripe-Signature": "t=1,v1=00"}
    )
    assert bad.status_code == 400
    for _ in range(2):  # the second delivery is ignored
        r = client.post(
            "/v1/billing/stripe/webhook",
            content=payload,
            headers={"Stripe-Signature": stripe_signature(payload, WEBHOOK_SECRET)},
        )
        assert r.status_code == 204
    client.app.state.services.principals.invalidate("dev:" + h["X-Dev-User"])  # type: ignore[attr-defined]
    assert client.get("/v1/me", headers=h).json()["plan"] == "plus"


def test_security_headers(client: TestClient) -> None:
    r = client.get("/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
    assert r.headers["X-Request-Id"]


def test_origin_guard(database_urls: tuple[str, str]) -> None:
    settings = Settings(env="test", database_url=database_urls[1], origin_verify_secret="s3cret")
    with TestClient(create_app(settings)) as c:
        assert c.get("/health").status_code == 403
        assert c.get("/health", headers={"X-Origin-Verify": "wrong"}).status_code == 403
        assert c.get("/health", headers={"X-Origin-Verify": "s3cret"}).status_code == 200

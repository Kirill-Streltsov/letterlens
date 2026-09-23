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


def main() -> None:
    settings = Settings(free_letters_per_month=1000)
    app = create_app(settings)
    services = app.state.services
    with services.container.db.session(DbContext.as_system()) as conn:
        existing = [s for s in R.counselling_services(conn) if s["name"].endswith("(Demo)")]
        tenant = (
            existing[0]["id"]
            if existing
            else R.create_tenant(
                conn,
                "Migrationsberatung Bochum (Demo)",
                "counselling",
                "Bochum",
                ["de", "tr", "ar", "uk"],
                True,
            )
        )
        if not existing:
            R.create_tenant(
                conn, "Jugendmigrationsdienst Essen (Demo)", "counselling", "Essen", ["de", "ru"], True
            )
        anna = R.resolve_user(conn, "dev:counsellor-anna")
        R.add_member(conn, tenant, str(anna["id"]), "admin")
        R.update_user(conn, str(anna["id"]), display_name="Anna (Beraterin)")
        client_user = R.resolve_user(conn, "dev:demo-client")
        R.update_user(conn, str(client_user["id"]), display_name="Olena K.", preferred_language="uk")

    picks = [generate_corpus(1, seed=77)[i] for i in (0, 5, 13, 16)] + [HANDWRITTEN[0], HANDWRITTEN[11]]
    languages = ["en", "uk", "tr", "ar", "en", "de"]
    with TestClient(app) as client:
        ids = []
        for letter, lang in zip(picks, languages, strict=True):
            body = {"document": to_document(letter).model_dump(mode="json"), "language": lang}
            r = client.post("/v1/letters", json=body, headers=CLIENT)
            r.raise_for_status()
            ids.append(r.json()["id"])
        share = {"tenant_id": tenant, "consent": True, "consent_text_version": "share-consent-v1"}
        for letter_id in ids[:3]:
            client.post(f"/v1/letters/{letter_id}/shares", json=share, headers=CLIENT).raise_for_status()
        cases = client.get("/v1/counsellor/cases", headers={"X-Dev-User": "counsellor-anna"}).json()
        if cases:
            client.post(
                f"/v1/shares/{cases[0]['share_id']}/messages",
                json={"text": "Добрий день! Чи можете ви надіслати мені копію договору оренди?"},
                headers=CLIENT,
            )
    print(f"seeded tenant {tenant}, {len(ids)} letters for demo-client")


if __name__ == "__main__":
    main()

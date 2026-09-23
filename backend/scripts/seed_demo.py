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


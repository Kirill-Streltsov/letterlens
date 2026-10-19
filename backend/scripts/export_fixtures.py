"""Write real API responses to contracts/fixtures/ for client contract tests (iOS, web).

Needs the local database (make migrate). tests/test_contract_fixtures.py checks that
the committed fixtures still validate against the current response models.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from letterlens.api.app import create_app
from letterlens.config import Settings
from letterlens.db import DbContext
from letterlens.db import repo as R
from letterlens.synthetic import generate_corpus, to_document

OUT = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
USER = {"X-Dev-User": "fixture-client"}


def save(name: str, data: object) -> None:
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = create_app(Settings(free_letters_per_month=1000))
    with TestClient(app) as c:
        letter = generate_corpus(1, seed=5)[0]
        created = c.post("/v1/letters", json={"document": to_document(letter).model_dump(mode="json"),
                                              "language": "en"}, headers=USER).json()
        save("create_letter", created)
        lid = created["id"]
        save("letter_view", c.get(f"/v1/letters/{lid}", headers=USER).json())
        save("letter_list", c.get("/v1/letters", headers=USER).json())
        save("me", c.get("/v1/me", headers=USER).json())
        save("languages", c.get("/v1/languages", headers=USER).json())
        save("question_refused", c.post(f"/v1/letters/{lid}/questions",
                                        json={"question": "Should I object?", "language": "en"},
                                        headers=USER).json())

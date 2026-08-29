"""Tenant isolation tests. They run as role letterlens_app with RLS active.

Each test states one isolation rule from docs/security/threat-model.md.
"""

from __future__ import annotations

import psycopg
import pytest

from letterlens.crypto import Kek, new_dek
from letterlens.db import Database, DbContext
from letterlens.db import repo as R
from letterlens.pipeline.state import PipelineState
from letterlens.synthetic import generate_corpus, to_document

pytestmark = pytest.mark.db
KEYS = R.KeyRing(Kek(new_dek()))


@pytest.fixture(scope="module")
def world(db: Database) -> dict[str, str]:
    """Two clients, two counselling tenants, one employer; one letter each, one share."""
    keys = KEYS
    ids: dict[str, str] = {}
    with db.session(DbContext.as_system()) as conn:
        for name in ("alice", "bob", "carol", "dave", "erin"):
            ids[name] = str(R.resolve_user(conn, f"rls:{name}")["id"])
        ids["t_x"] = R.create_tenant(conn, "Service X", "counselling", "Bochum", ["de"], True)
        ids["t_y"] = R.create_tenant(conn, "Service Y", "counselling", "Essen", ["de"], True)
        ids["t_emp"] = R.create_tenant(conn, "Employer", "employer", None, [], False)
        R.add_member(conn, ids["t_x"], ids["carol"], "counsellor")
        R.add_member(conn, ids["t_y"], ids["dave"], "counsellor")
        R.add_member(conn, ids["t_emp"], ids["erin"], "employee")
        doc = to_document(generate_corpus(1)[0])
        for owner in ("alice", "bob"):
            state = PipelineState(letter_id=R.new_id(), owner_id=ids[owner], document=doc)
            R.insert_letter(conn, keys, state, 30)
            ids[f"letter_{owner}"] = state.letter_id
    with db.session(DbContext(user_id=ids["alice"])) as conn:
        share = R.create_share(
            conn, ids["letter_alice"], ids["alice"], ids["t_x"], "share-consent-v1", 30, "tr"
        )
        ids["share"] = share["id"]
    return ids



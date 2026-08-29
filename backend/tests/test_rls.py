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


def ctx(world: dict[str, str], who: str, *tenants: str) -> DbContext:
    return DbContext(user_id=world[who], tenant_ids=tuple(world[t] for t in tenants))


def visible_letters(db: Database, context: DbContext) -> set[str]:
    with db.session(context) as conn:
        return {r["id"] for r in conn.execute("SELECT id::text FROM letters").fetchall()}


def test_app_role_cannot_bypass_rls(db: Database) -> None:
    with db.session(DbContext()) as conn:
        row = conn.execute(
            "SELECT rolbypassrls, rolsuper FROM pg_roles WHERE rolname = current_user"
        ).fetchone()
    assert row == {"rolbypassrls": False, "rolsuper": False}


def test_no_context_sees_nothing(db: Database, world: dict[str, str]) -> None:
    assert visible_letters(db, DbContext()) == set()


def test_client_sees_only_own_letters(db: Database, world: dict[str, str]) -> None:
    assert visible_letters(db, ctx(world, "alice")) == {world["letter_alice"]}
    assert visible_letters(db, ctx(world, "bob")) == {world["letter_bob"]}


def test_client_cannot_update_or_delete_foreign_letter(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "bob")) as conn:
        assert R.delete_letter(conn, world["letter_alice"]) is None
        updated = conn.execute(
            "UPDATE letters SET status = 'failed' WHERE id = %s RETURNING id", (world["letter_alice"],)
        ).fetchone()
        assert updated is None


def test_client_cannot_insert_letter_for_someone_else(db: Database, world: dict[str, str]) -> None:
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.session(ctx(world, "bob")) as conn:
        conn.execute(
            "INSERT INTO letters (owner_id, status, language, state, expires_at)"
            " VALUES (%s, 'received', 'en', '\\x00', now())",
            (world["alice"],),
        )


def test_counsellor_sees_shared_letter_only(db: Database, world: dict[str, str]) -> None:
    assert visible_letters(db, ctx(world, "carol", "t_x")) == {world["letter_alice"]}


def test_other_tenant_sees_nothing(db: Database, world: dict[str, str]) -> None:
    assert visible_letters(db, ctx(world, "dave", "t_y")) == set()
    with db.session(ctx(world, "dave", "t_y")) as conn:
        assert R.get_share(conn, world["share"]) is None


def test_forged_tenant_claim_without_share_sees_nothing(db: Database, world: dict[str, str]) -> None:
    # Even if a bug put the wrong tenant in the context, only shared letters are visible.
    assert visible_letters(db, ctx(world, "dave", "t_x", "t_y")) == {world["letter_alice"]}
    assert world["letter_bob"] not in visible_letters(db, ctx(world, "dave", "t_x", "t_y"))


def test_counsellor_cannot_change_letter(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "carol", "t_x")) as conn:
        assert R.delete_letter(conn, world["letter_alice"]) is None


def test_counsellor_can_update_case_status(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "carol", "t_x")) as conn:
        assert R.update_case(conn, world["share"], "in_progress", None)
    with db.session(ctx(world, "dave", "t_y")) as conn:
        assert not R.update_case(conn, world["share"], "closed", None)



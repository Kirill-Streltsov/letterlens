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


def test_revoked_share_hides_letter(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "alice")) as conn:
        assert R.revoke_share(conn, world["share"])
    try:
        assert visible_letters(db, ctx(world, "carol", "t_x")) == set()
    finally:
        with db.session(DbContext.as_system()) as conn:
            conn.execute("UPDATE shares SET revoked_at = NULL WHERE id = %s", (world["share"],))


def test_expired_share_hides_letter(db: Database, world: dict[str, str]) -> None:
    with db.session(DbContext.as_system()) as conn:
        conn.execute(
            "UPDATE shares SET expires_at = now() - interval '1 minute' WHERE id = %s", (world["share"],)
        )
    try:
        assert visible_letters(db, ctx(world, "carol", "t_x")) == set()
    finally:
        with db.session(DbContext.as_system()) as conn:
            conn.execute(
                "UPDATE shares SET expires_at = now() + interval '30 days' WHERE id = %s", (world["share"],)
            )


def test_letters_cannot_be_shared_with_employers(db: Database, world: dict[str, str]) -> None:
    with pytest.raises(psycopg.errors.CheckViolation), db.session(ctx(world, "bob")) as conn:
        R.create_share(conn, world["letter_bob"], world["bob"], world["t_emp"], "share-consent-v1", 30, "en")


def test_employee_membership_grants_no_letter_access(db: Database, world: dict[str, str]) -> None:
    assert visible_letters(db, ctx(world, "erin", "t_emp")) == set()


def test_keys_of_other_users_are_hidden(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "bob")) as conn:
        rows = conn.execute("SELECT user_id::text FROM user_keys").fetchall()
    assert {r["user_id"] for r in rows} <= {world["bob"]}


def test_audit_log_is_append_only(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "alice")) as conn:
        R.audit(conn, world["alice"], "test.event", "letter", world["letter_alice"])
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.session(ctx(world, "alice")) as conn:
        conn.execute("DELETE FROM audit_log")
    with pytest.raises(psycopg.errors.InsufficientPrivilege), db.session(DbContext.as_system()) as conn:
        conn.execute("UPDATE audit_log SET action = 'x'")


def test_ledger_rows_of_others_are_hidden(db: Database, world: dict[str, str]) -> None:
    with db.session(DbContext.as_system()) as conn:
        conn.execute(
            "INSERT INTO llm_calls (task, provider, model, prompt_version, input_tokens,"
            " output_tokens, list_price_usd, latency_ms, attempts, fallback_used, ok, user_id)"
            " VALUES ('extract','p','m','v',1,1,0,1,1,false,true,%s)",
            (world["alice"],),
        )
    with db.session(ctx(world, "bob")) as conn:
        assert conn.execute(
            "SELECT count(*) AS n FROM llm_calls WHERE user_id = %s", (world["alice"],)
        ).fetchone() == {"n": 0}


def test_messages_visible_to_participants_only(db: Database, world: dict[str, str]) -> None:
    with db.session(ctx(world, "carol", "t_x")) as conn:
        share = R.get_share(conn, world["share"])
        assert share is not None
        # The counsellor can read the owner's wrapped key through the active share.
        R.insert_message(conn, R.KeyRing(KEYS.kek), share, world["carol"], "counsellor", b"{}")
    for who, tenants, expected in (
        ("alice", (), 1),
        ("carol", ("t_x",), 1),
        ("dave", ("t_y",), 0),
        ("bob", (), 0),
    ):
        with db.session(ctx(world, who, *tenants)) as conn:
            n = conn.execute("SELECT count(*) AS n FROM messages").fetchone()
        assert n == {"n": expected}, who


def test_admin_cli_creates_tenant_and_invite(
    database_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from letterlens import admin
    from letterlens.config import get_settings

    monkeypatch.setenv("LETTERLENS_DATABASE_URL", database_urls[1])
    monkeypatch.delenv("LETTERLENS_SSM_PREFIX", raising=False)
    get_settings.cache_clear()
    try:
        assert admin.main(["create-tenant", "CLI Service", "--city", "Dortmund"]) == 0
        tenant_id = capsys.readouterr().out.strip()
        assert admin.main(["invite", tenant_id]) == 0
        assert len(capsys.readouterr().out.strip()) == 14
    finally:
        get_settings.cache_clear()


def test_retention_job_purges_old_ledger_rows_only_in_system_context(
    db: Database, world: dict[str, str]
) -> None:
    with db.session(DbContext.as_system()) as conn:
        conn.execute(
            "INSERT INTO llm_calls (created_at, task, provider, model, prompt_version, input_tokens,"
            " output_tokens, list_price_usd, latency_ms, attempts, fallback_used, ok)"
            " VALUES (now() - interval '14 months','extract','p','m','old',1,1,0,1,1,false,true)"
        )
    with db.session(ctx(world, "alice")) as conn:
        conn.execute("DELETE FROM llm_calls")  # allowed statement, but RLS matches no rows
    with db.session(DbContext.as_system()) as conn:
        assert conn.execute(
            "SELECT count(*) AS n FROM llm_calls WHERE prompt_version = 'old'"
        ).fetchone() == {"n": 1}
        R.purge_expired(conn)
        assert conn.execute(
            "SELECT count(*) AS n FROM llm_calls WHERE prompt_version = 'old'"
        ).fetchone() == {"n": 0}

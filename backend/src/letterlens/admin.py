"""Operator commands. They run in the trusted system context, so only operators run them.

  uv run python -m letterlens.admin create-tenant "Migrationsberatung Bochum" --city Bochum --languages de,tr,ar
  uv run python -m letterlens.admin invite <tenant-id> --role admin
  uv run python -m letterlens.admin list-tenants
  uv run python -m letterlens.admin purge-expired

Set LETTERLENS_DATABASE_URL (app role) and, for production, LETTERLENS_SSM_PREFIX or the env values.
"""

from __future__ import annotations

import argparse
import secrets
import sys

from letterlens.config import get_settings
from letterlens.db import Database, DbContext
from letterlens.db import repo as R
from letterlens.secrets import load_ssm_into_env

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_code() -> str:
    return "-".join("".join(secrets.choice(ALPHABET) for _ in range(4)) for _ in range(3))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="letterlens.admin")
    sub = parser.add_subparsers(dest="command", required=True)
    tenant = sub.add_parser("create-tenant", help="create a counselling service or an employer")
    tenant.add_argument("name")
    tenant.add_argument("--kind", choices=["counselling", "employer"], default="counselling")
    tenant.add_argument("--city")
    tenant.add_argument("--languages", default="de")
    tenant.add_argument("--hidden", action="store_true", help="do not list it in the app")
    tenant.add_argument("--seats", type=int, default=0)
    invite = sub.add_parser("invite", help="create a one-time invite code (valid 14 days)")
    invite.add_argument("tenant_id")
    invite.add_argument("--role", choices=["counsellor", "admin", "employee"], default="admin")
    sub.add_parser("list-tenants")
    sub.add_parser("purge-expired")
    args = parser.parse_args(argv)

    load_ssm_into_env()
    db = Database(get_settings().database_url.get_secret_value(), max_size=1)
    with db.session(DbContext.as_system()) as conn:
        if args.command == "create-tenant":
            tid = R.create_tenant(
                conn,
                args.name,
                args.kind,
                args.city,
                [x.strip() for x in args.languages.split(",") if x.strip()],
                not args.hidden,
                args.seats,
            )
            R.audit(conn, None, "admin.tenant.create", "tenant", tid, tenant_id=tid)
            print(tid)
        elif args.command == "invite":
            code = new_code()
            R.create_invite(conn, args.tenant_id, args.role, None, code)
            R.audit(
                conn,
                None,
                "admin.invite.create",
                "tenant",
                args.tenant_id,
                tenant_id=args.tenant_id,
                details={"role": args.role},
            )
            print(code)
        elif args.command == "list-tenants":
            for row in conn.execute(
                "SELECT id::text, kind, name, city, seats FROM tenants ORDER BY name"
            ).fetchall():
                print(
                    f"{row['id']}  {row['kind']:<11} {row['name']} ({row['city'] or '-'}) seats={row['seats']}"
                )
        elif args.command == "purge-expired":
            deleted, _ = R.purge_expired(conn)
            print(f"deleted {deleted} letters (images: run the retention Lambda)")
    db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

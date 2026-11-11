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


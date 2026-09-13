"""Load configuration secrets from AWS SSM Parameter Store at cold start.

Every parameter under LETTERLENS_SSM_PREFIX (for example /letterlens/prod/)
becomes an environment variable: /letterlens/prod/database_url ->
LETTERLENS_DATABASE_URL. SecureString parameters are decrypted. Standard
parameters are free, unlike Secrets Manager (ADR-0002).
"""

from __future__ import annotations

import os
from typing import Any


def load_ssm_into_env(prefix: str | None = None, client: Any = None) -> list[str]:
    prefix = prefix or os.environ.get("LETTERLENS_SSM_PREFIX", "")
    if not prefix:
        return []
    if client is None:
        import boto3

        client = boto3.client("ssm")
    loaded = []
    paginator = client.get_paginator("get_parameters_by_path")
    for page in paginator.paginate(Path=prefix, Recursive=False, WithDecryption=True):
        for param in page["Parameters"]:
            name = param["Name"].rsplit("/", 1)[-1]
            key = f"LETTERLENS_{name.upper()}"
            os.environ.setdefault(key, param["Value"])  # explicit env vars win
            loaded.append(key)
    return loaded

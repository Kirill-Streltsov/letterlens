"""Cognito access-token verification with a locally generated key pair."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from letterlens.api.auth import AuthError, authenticate, issuer, verify_cognito_token
from letterlens.config import Settings

SETTINGS = Settings(
    env="test", auth_mode="cognito", cognito_user_pool_id="eu-central-1_TEST", cognito_client_ids=["client-1"]
)
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)



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


@dataclass
class FakeJwks:
    key: Any

    def get_signing_key_from_jwt(self, token: str) -> Any:
        @dataclass
        class Signing:
            key: Any

        return Signing(self.key)


def token(**claims: Any) -> str:
    now = int(time.time())
    base = {
        "sub": "abc",
        "iss": issuer(SETTINGS),
        "token_use": "access",
        "client_id": "client-1",
        "iat": now,
        "exp": now + 600,
        "cognito:groups": ["counsellor"],
    }
    base.update(claims)
    return jwt.encode(base, KEY, algorithm="RS256", headers={"kid": "k1"})


JWKS = FakeJwks(KEY.public_key())


def test_valid_token() -> None:
    identity = verify_cognito_token(token(), SETTINGS, JWKS)
    assert identity.sub == "abc" and "counsellor" in identity.groups


@pytest.mark.parametrize(
    "claims",
    [
        {"exp": int(time.time()) - 120},
        {"token_use": "id"},
        {"client_id": "other"},
        {"iss": "https://evil.example"},
    ],
)
def test_invalid_tokens(claims: dict[str, Any]) -> None:
    with pytest.raises(AuthError):
        verify_cognito_token(token(**claims), SETTINGS, JWKS)


def test_wrong_key() -> None:
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(AuthError):
        verify_cognito_token(token(), SETTINGS, FakeJwks(other.public_key()))


def test_dev_mode_header() -> None:
    dev = Settings(env="test", auth_mode="dev")
    identity = authenticate({"x-dev-user": "alice", "x-dev-groups": "counsellor"}, dev)
    assert identity.sub == "dev:alice"
    with pytest.raises(AuthError):
        authenticate({}, dev)


def test_dev_mode_is_refused_in_prod() -> None:
    with pytest.raises(ValueError, match="auth_mode=dev"):
        Settings(env="prod", auth_mode="dev", llm_provider="mistral", llm_training_opt_out_confirmed=True)


def test_mistral_in_prod_needs_opt_out_confirmation() -> None:
    with pytest.raises(ValueError, match="training opt-out"):
        Settings(env="prod", auth_mode="cognito", llm_provider="mistral")

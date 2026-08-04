"""Authentication: Cognito access tokens (production) or a dev header (local only)."""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from letterlens.config import AuthMode, Settings


class AuthError(Exception):
    pass


@dataclass(frozen=True)
class Identity:
    sub: str
    groups: frozenset[str] = field(default_factory=frozenset)


@lru_cache(maxsize=4)
def _jwks_client(url: str) -> PyJWKClient:
    return PyJWKClient(url, cache_keys=True, lifespan=3600)


def issuer(settings: Settings) -> str:
    return (
        f"https://cognito-idp.{settings.cognito_region}.amazonaws.com/"
        f"{settings.cognito_user_pool_id}"
    )


def verify_cognito_token(token: str, settings: Settings, jwks: Any | None = None) -> Identity:
    iss = issuer(settings)
    client = jwks or _jwks_client(f"{iss}/.well-known/jwks.json")
    try:
        key = client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            key=key,
            algorithms=["RS256"],
            issuer=iss,
            options={"require": ["exp", "iat", "sub", "token_use"], "verify_aud": False},

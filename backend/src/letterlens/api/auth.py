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



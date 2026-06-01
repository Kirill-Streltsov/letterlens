"""Runtime configuration.

All settings come from environment variables with the prefix ``LETTERLENS_``.
The settings object is immutable and is created once per process.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(StrEnum):
    TEST = "test"
    DEV = "dev"
    PROD = "prod"



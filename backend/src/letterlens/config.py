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


class AuthMode(StrEnum):
    COGNITO = "cognito"
    # Dev mode trusts an unsigned header. It is refused when env=prod.
    DEV = "dev"


class PipelineRunner(StrEnum):
    INPROCESS = "inprocess"
    STEPFUNCTIONS = "stepfunctions"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LETTERLENS_", frozen=True, extra="ignore")

    env: Environment = Environment.DEV
    log_level: str = "INFO"
    # Public base URL of the web app. Used for CORS in dev and for Stripe redirect URLs.
    public_web_url: str = "http://localhost:3000"

    # --- Database -------------------------------------------------------
    database_url: SecretStr = SecretStr(
        "postgresql://letterlens_app:letterlens_app@localhost:5433/letterlens"
    )
    # Owner role URL. Only the migration command uses it.
    database_admin_url: SecretStr | None = None


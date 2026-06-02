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

    # --- Auth -----------------------------------------------------------
    auth_mode: AuthMode = AuthMode.DEV
    cognito_region: str = "eu-central-1"
    cognito_user_pool_id: str = ""
    cognito_client_ids: list[str] = Field(default_factory=list)

    # --- Encryption -----------------------------------------------------
    # 32-byte key encryption key, base64. In AWS it comes from SSM Parameter Store.
    kek_base64: SecretStr | None = None
    kek_ssm_parameter: str = ""

    # --- Storage --------------------------------------------------------
    letters_bucket: str = ""
    aws_region: str = "eu-central-1"

    # --- Pipeline -------------------------------------------------------
    pipeline_runner: PipelineRunner = PipelineRunner.INPROCESS
    state_machine_arn: str = ""


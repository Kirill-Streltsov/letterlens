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

    # --- LLM gateway ----------------------------------------------------
    # "fake" is deterministic and offline. "mistral" is the free EU default.
    llm_provider: Literal["fake", "mistral", "openai_compat", "anthropic", "bedrock"] = "fake"
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.mistral.ai/v1"
    llm_model_extract: str = "mistral-small-latest"
    llm_model_explain: str = "mistral-medium-latest"
    llm_model_guard: str = "mistral-small-latest"
    llm_fallback_models: list[str] = Field(default_factory=lambda: ["mistral-small-latest"])
    llm_timeout_seconds: float = 45.0
    # The operator confirms that the provider account does not train on API data.
    llm_training_opt_out_confirmed: bool = False
    embedding_model: str = "mistral-embed"
    embedding_dim: int = 1024

    # --- Budgets and limits ----------------------------------------------
    monthly_llm_budget_usd: float = 20.0
    user_daily_token_budget: int = 200_000
    free_letters_per_month: int = 3
    rate_limit_per_minute: int = 30

    # --- Data protection -------------------------------------------------
    default_retention_days: int = 30
    share_default_days: int = 30

    # --- Billing ---------------------------------------------------------
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_plus: str = ""
    stripe_price_seat: str = ""
    appstore_bundle_id: str = "app.letterlens.ios"
    appstore_product_plus: str = "app.letterlens.plus.monthly"
    appstore_environment: Literal["Sandbox", "Production"] = "Sandbox"

    # --- Languages -------------------------------------------------------
    languages_file: str = ""

    @model_validator(mode="after")
    def _guard_prod(self) -> Settings:
        if self.env is Environment.PROD:
            if self.auth_mode is AuthMode.DEV:
                raise ValueError("auth_mode=dev is not allowed when env=prod")
            if self.llm_provider == "fake":
                raise ValueError("llm_provider=fake is not allowed when env=prod")
            if self.llm_provider == "mistral" and not self.llm_training_opt_out_confirmed:
                raise ValueError(
                    "Confirm the Mistral training opt-out "
                    "(LETTERLENS_LLM_TRAINING_OPT_OUT_CONFIRMED=true) before env=prod"
                )
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

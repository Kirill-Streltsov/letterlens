"""Types shared by the LLM gateway and its providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Protocol


class Task(StrEnum):
    EXTRACT = "extract"
    EXPLAIN = "explain"
    ANSWER = "answer"
    GUARD = "guard"
    BACKTRANSLATE = "backtranslate"
    TRANSLATE_REPLY = "translate_reply"
    TRANSLATE_EXPLANATION = "translate_explanation"


@dataclass(frozen=True)
class LLMRequest:
    task: Task
    model: str
    system: str
    user: str
    json_schema: dict[str, Any] | None
    schema_name: str = "result"
    max_tokens: int = 4000
    # Structured inputs for the offline provider. Real providers ignore this field.
    context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    request_id: str | None = None


@dataclass(frozen=True)
class LLMCall:
    """One gateway call. Stored in the cost ledger (table llm_calls). Contains no letter text."""

    task: Task
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    list_price_usd: float
    latency_ms: int
    attempts: int
    fallback_used: bool
    ok: bool
    error: str | None = None
    user_id: str | None = None
    letter_id: str | None = None


class LLMError(Exception):
    """Base class for gateway errors."""


class RetryableError(LLMError):
    """Timeouts, rate limits and server errors. The gateway retries and then falls back."""


class PermanentError(LLMError):
    """Bad request, auth error, refusal. The gateway does not retry the same model."""


class SchemaError(LLMError):
    """The model output does not match the schema after the repair attempt."""


class BudgetExceededError(LLMError):
    """A spend or token budget would be exceeded. The pipeline switches to degraded mode."""


class Provider(Protocol):
    name: str

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse: ...

    def embed(self, texts: list[str], model: str, timeout: float) -> list[list[float]]: ...

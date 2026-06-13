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



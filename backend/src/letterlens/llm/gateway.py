"""LLM gateway: the only path from application code to a model.

Responsibilities
- Route each task to a model chain (primary, then fallbacks).
- Enforce budgets before every call (monthly spend, tokens per user per day).
- Retry transient errors with exponential backoff and jitter.
- Validate output against a strict schema; one repair attempt on invalid JSON.
- Record every call in the cost ledger: tokens, list price, latency, prompt version.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError

from letterlens.config import Settings
from letterlens.llm.pricing import list_price_usd
from letterlens.llm.schema import strict_schema
from letterlens.llm.types import (
    BudgetExceededError,
    LLMCall,
    LLMError,
    LLMRequest,
    PermanentError,
    Provider,
    RetryableError,
    SchemaError,
    Task,
)

log = logging.getLogger(__name__)

MAX_ATTEMPTS_PER_MODEL = 3
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class UsageLedger(Protocol):
    def month_spend_usd(self) -> float: ...

    def user_tokens_today(self, user_id: str) -> int: ...

    def record(self, call: LLMCall) -> None: ...


@dataclass
class InMemoryLedger:
    calls: list[LLMCall] = field(default_factory=list)

    def month_spend_usd(self) -> float:
        return sum(c.list_price_usd for c in self.calls)

    def user_tokens_today(self, user_id: str) -> int:
        return sum(c.input_tokens + c.output_tokens for c in self.calls if c.user_id == user_id)

    def record(self, call: LLMCall) -> None:
        self.calls.append(call)


def parse_json_output[M: BaseModel](text: str, schema_model: type[M]) -> M:
    cleaned = _FENCE.sub("", text.strip())
    return schema_model.model_validate(json.loads(cleaned))


class Gateway:
    def __init__(
        self,
        provider: Provider,
        settings: Settings,
        ledger: UsageLedger,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.provider = provider
        self.settings = settings
        self.ledger = ledger
        self._sleep = sleep
        self._schemas: dict[type[BaseModel], dict[str, Any]] = {}

    def models_for(self, task: Task) -> list[str]:
        s = self.settings
        primary = {
            Task.EXTRACT: s.llm_model_extract,
            Task.EXPLAIN: s.llm_model_explain,
            Task.ANSWER: s.llm_model_explain,
            Task.TRANSLATE_REPLY: s.llm_model_explain,
            Task.GUARD: s.llm_model_guard,
            Task.BACKTRANSLATE: s.llm_model_guard,
        }[task]
        return list(dict.fromkeys([primary, *s.llm_fallback_models]))

    def _check_budget(self, user_id: str | None) -> None:
        if self.ledger.month_spend_usd() >= self.settings.monthly_llm_budget_usd:
            raise BudgetExceededError("monthly LLM budget reached")
        if user_id and self.ledger.user_tokens_today(user_id) >= self.settings.user_daily_token_budget:
            raise BudgetExceededError("daily token budget for this user reached")

    def _schema(self, model: type[BaseModel]) -> dict[str, Any]:
        if model not in self._schemas:
            self._schemas[model] = strict_schema(model)
        return self._schemas[model]

    def generate[M: BaseModel](
        self,
        task: Task,
        schema_model: type[M],
        system: str,
        user: str,
        prompt_version: str,
        context: dict[str, Any] | None = None,
        user_id: str | None = None,
        letter_id: str | None = None,
        max_tokens: int = 4000,
    ) -> M:
        self._check_budget(user_id)
        chain = self.models_for(task)
        last_error: Exception | None = None
        for model_index, model in enumerate(chain):
            request = LLMRequest(
                task=task,
                model=model,
                system=system,
                user=user,
                json_schema=self._schema(schema_model),
                schema_name=schema_model.__name__,
                max_tokens=max_tokens,

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



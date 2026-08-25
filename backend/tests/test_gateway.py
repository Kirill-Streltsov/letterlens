"""Gateway resilience: retries, fallbacks, budgets, schema repair, cost ledger."""

from __future__ import annotations

import json
from collections import deque

import pytest

from letterlens.config import Settings
from letterlens.llm.gateway import Gateway, InMemoryLedger
from letterlens.llm.outputs import GuardDecision
from letterlens.llm.types import (
    BudgetExceededError,
    LLMCall,
    LLMRequest,
    LLMResponse,
    PermanentError,
    RetryableError,
    SchemaError,
    Task,
)

VALID = json.dumps({"category": "general_information", "rationale": "ok"})



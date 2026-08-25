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


class ScriptedProvider:
    name = "scripted"

    def __init__(self, script: list[object]) -> None:
        self.script = deque(script)
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse:
        self.requests.append(request)
        step = self.script.popleft()
        if isinstance(step, Exception):
            raise step
        return LLMResponse(
            text=str(step),
            model=request.model,
            provider=self.name,
            input_tokens=100,
            output_tokens=20,
            latency_ms=5,
        )

    def embed(self, texts: list[str], model: str, timeout: float) -> list[list[float]]:
        return [[0.0] for _ in texts]



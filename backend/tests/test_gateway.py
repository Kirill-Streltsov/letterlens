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


def gateway(script: list[object], **settings: object) -> tuple[Gateway, ScriptedProvider, InMemoryLedger]:
    provider = ScriptedProvider(script)
    ledger = InMemoryLedger()
    base = {"llm_model_guard": "mistral-small-latest", "llm_fallback_models": ["backup-model"]}
    gw = Gateway(provider, Settings(env="test", **{**base, **settings}), ledger, sleep=lambda _: None)
    return gw, provider, ledger


def call(gw: Gateway, user_id: str | None = "u1") -> GuardDecision:
    return gw.generate(Task.GUARD, GuardDecision, "sys", "user", "guard-v2", user_id=user_id)


def test_success_records_cost() -> None:
    gw, _, ledger = gateway([VALID])
    assert call(gw).category == "general_information"
    [entry] = ledger.calls
    assert entry.ok and entry.list_price_usd > 0 and entry.prompt_version == "guard-v2"


def test_retry_then_success() -> None:
    gw, provider, ledger = gateway([RetryableError("429"), VALID])
    call(gw)
    assert len(provider.requests) == 2
    assert [c.ok for c in ledger.calls] == [False, True]



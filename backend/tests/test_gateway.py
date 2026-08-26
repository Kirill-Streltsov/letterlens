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


def test_fallback_after_permanent_error() -> None:
    gw, provider, ledger = gateway([PermanentError("400"), VALID])
    call(gw)
    assert [r.model for r in provider.requests] == ["mistral-small-latest", "backup-model"]
    assert ledger.calls[-1].fallback_used


def test_fallback_after_retries_exhausted() -> None:
    gw, provider, _ = gateway([RetryableError("x")] * 3 + [VALID])
    call(gw)
    assert provider.requests[-1].model == "backup-model"


def test_schema_repair_once() -> None:
    gw, provider, _ = gateway(["not json", VALID])
    call(gw)
    assert "not valid JSON" in provider.requests[1].user


def test_schema_failure_after_repair_falls_back_then_raises() -> None:
    gw, _, _ = gateway(["bad", "bad", "bad", "bad"])
    with pytest.raises(SchemaError):
        call(gw)


def test_code_fences_are_accepted() -> None:
    gw, _, _ = gateway([f"```json\n{VALID}\n```"])
    assert call(gw).rationale == "ok"


def test_monthly_budget_blocks_before_call() -> None:
    gw, provider, ledger = gateway([VALID], monthly_llm_budget_usd=0.001)
    ledger.record(LLMCall(Task.GUARD, "x", "m", "v", 0, 0, 1.0, 0, 1, False, True))
    with pytest.raises(BudgetExceededError):
        call(gw)
    assert provider.requests == []


def test_user_token_budget() -> None:
    gw, _, ledger = gateway([VALID], user_daily_token_budget=50)
    ledger.record(LLMCall(Task.GUARD, "x", "m", "v", 40, 20, 0.0, 0, 1, False, True, user_id="u1"))
    with pytest.raises(BudgetExceededError):
        call(gw)
    gw2, _, _ = gateway([VALID], user_daily_token_budget=50)
    assert call(gw2, user_id="other")


def test_strict_schema_is_sent() -> None:
    gw, provider, _ = gateway([VALID])
    call(gw)
    schema = provider.requests[0].json_schema
    assert schema is not None
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == {"category", "rationale"}

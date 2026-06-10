"""Provider for Claude models: Claude API or Amazon Bedrock (Mantle client).

This is the paid production profile (ADR-0003). Structured output uses
``output_config.format``; depth is controlled by ``output_config.effort``.
On the Claude API, server-side refusal fallbacks are enabled.
"""

from __future__ import annotations

import time
from typing import Any

import anthropic

from letterlens.llm.types import (
    LLMRequest,
    LLMResponse,
    PermanentError,
    RetryableError,
    Task,
)

# Cheaper tasks need less reasoning depth.
EFFORT: dict[Task, str] = {
    Task.EXTRACT: "medium",
    Task.EXPLAIN: "medium",
    Task.ANSWER: "medium",
    Task.GUARD: "low",
    Task.BACKTRANSLATE: "low",
    Task.TRANSLATE_REPLY: "low",
}

# Models that accept the server-side refusal fallback parameter.
_SERVER_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-2"}


class AnthropicProvider:
    def __init__(self, backend: str = "anthropic", api_key: str | None = None, region: str = "") -> None:
        self.name = "bedrock" if backend == "bedrock" else "anthropic"
        self._client: Any
        if backend == "bedrock":
            self._client = anthropic.AnthropicBedrockMantle(aws_region=region)
        else:
            self._client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse:
        output_config: dict[str, Any] = {"effort": EFFORT.get(request.task, "medium")}
        if request.json_schema is not None:
            output_config["format"] = {"type": "json_schema", "schema": request.json_schema}
        kwargs: dict[str, Any] = {
            "model": request.model,
            "max_tokens": request.max_tokens,
            "system": request.system,
            "messages": [{"role": "user", "content": request.user}],
            "output_config": output_config,
            "timeout": timeout,
        }
        started = time.perf_counter()
        try:
            if self.name == "anthropic" and request.model in _SERVER_FALLBACK_MODELS:
                response = self._client.beta.messages.create(
                    **kwargs, betas=["server-side-fallback-2026-07-01"], fallbacks="default"
                )
            else:
                response = self._client.messages.create(**kwargs)
        except (anthropic.RateLimitError, anthropic.APIConnectionError) as exc:
            raise RetryableError(f"{self.name}: {type(exc).__name__}") from exc
        except anthropic.APIStatusError as exc:
            if exc.status_code >= 500 or exc.status_code in {408, 409, 429}:
                raise RetryableError(f"{self.name}: HTTP {exc.status_code}") from exc
            raise PermanentError(f"{self.name}: HTTP {exc.status_code}") from exc
        latency = int((time.perf_counter() - started) * 1000)


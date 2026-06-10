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


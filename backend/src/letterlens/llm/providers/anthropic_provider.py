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


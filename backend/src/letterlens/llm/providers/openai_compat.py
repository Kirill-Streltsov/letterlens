"""Provider for OpenAI-compatible chat APIs: Mistral (default), Groq, Ollama, vLLM.

Uses plain HTTP through httpx, so one adapter covers every compatible host.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from letterlens.llm.types import (
    LLMRequest,
    LLMResponse,
    PermanentError,
    RetryableError,
)

_RETRYABLE_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}



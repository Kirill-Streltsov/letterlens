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


class OpenAICompatibleProvider:
    def __init__(self, name: str, base_url: str, api_key: str | None) -> None:
        self.name = name
        self._base = base_url.rstrip("/")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._client = httpx.Client(headers=headers)

    def _post(self, path: str, payload: dict[str, Any], timeout: float) -> httpx.Response:
        try:
            response = self._client.post(f"{self._base}{path}", json=payload, timeout=timeout)
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            raise RetryableError(f"{self.name}: transport error {type(exc).__name__}") from exc
        if response.status_code in _RETRYABLE_STATUS:
            raise RetryableError(f"{self.name}: HTTP {response.status_code}")
        if response.status_code >= 400:
            # The body can echo the prompt. Never include it in the error text.
            raise PermanentError(f"{self.name}: HTTP {response.status_code}")
        return response

    def complete(self, request: LLMRequest, timeout: float) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "max_tokens": request.max_tokens,
            "temperature": 0.0 if request.task in {"extract", "guard"} else 0.2,
        }
        if request.json_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",

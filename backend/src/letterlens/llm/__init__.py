"""LLM gateway and providers."""

from __future__ import annotations

from letterlens.config import Settings
from letterlens.llm.gateway import Gateway, InMemoryLedger, UsageLedger
from letterlens.llm.types import Provider, Task


def build_provider(settings: Settings) -> Provider:
    key = settings.llm_api_key.get_secret_value() if settings.llm_api_key else None
    match settings.llm_provider:
        case "fake":
            from letterlens.llm.providers.fake import FakeProvider

            return FakeProvider()
        case "mistral" | "openai_compat":
            from letterlens.llm.providers.openai_compat import OpenAICompatibleProvider

            return OpenAICompatibleProvider(settings.llm_provider, settings.llm_base_url, key)
        case "anthropic":
            from letterlens.llm.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider("anthropic", api_key=key)
        case "bedrock":
            from letterlens.llm.providers.anthropic_provider import AnthropicProvider

            return AnthropicProvider("bedrock", region=settings.aws_region)
    raise ValueError(f"unknown provider {settings.llm_provider}")


def build_gateway(settings: Settings, ledger: UsageLedger | None = None) -> Gateway:
    return Gateway(build_provider(settings), settings, ledger or InMemoryLedger())


__all__ = ["Gateway", "InMemoryLedger", "Task", "UsageLedger", "build_gateway", "build_provider"]

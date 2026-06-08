"""List prices per million tokens, in USD.

The ledger records the list price of every call, also on free tiers. This
answers "what would this request cost on a paid plan?" and feeds the spend
budget. Prices are illustrative and must be checked against the provider's
price page before a budget decision (docs/operations/cost.md).
"""

from __future__ import annotations

# model id prefix -> (input USD / 1M tokens, output USD / 1M tokens)
PRICES: dict[str, tuple[float, float]] = {
    "mistral-small": (0.10, 0.30),
    "mistral-medium": (0.40, 2.00),
    "mistral-large": (2.00, 6.00),
    "mistral-embed": (0.10, 0.0),
    "claude-opus-5-5": (4.00, 20.00),
    "claude-sonnet-5-5": (2.00, 10.00),
    "claude-haiku-5-5": (0.10, 0.50),
    "anthropic.claude-opus-5-5": (4.00, 20.00),
    "fake": (0.0, 0.0),
}

DEFAULT_PRICE = (1.0, 3.0)  # conservative for unknown models


def price_for(model: str) -> tuple[float, float]:
    for prefix in sorted(PRICES, key=len, reverse=True):
        if model.startswith(prefix):
            return PRICES[prefix]
    return DEFAULT_PRICE


def list_price_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = price_for(model)
    return round((input_tokens * price_in + output_tokens * price_out) / 1_000_000, 6)

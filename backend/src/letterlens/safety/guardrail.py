"""Legal-advice guardrail.

LetterLens explains what a letter says. It does not assess the reader's
individual legal case (§ 2 (1) RDG). This module decides whether a user
question asks for such an assessment, and whether a generated text gives one.

Layer 1 is a multilingual rule set: fast, free, explainable.
Layer 2 is an LLM classifier (see letterlens.pipeline.qa). The policy blocks a
question when either layer flags it. Measured catch rate and false-positive
rate per layer are in evals/reports/guardrail.json.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class Verdict(StrEnum):
    ALLOW = "allow"
    LEGAL_ADVICE = "legal_advice"
    INJECTION = "prompt_injection"


@dataclass(frozen=True, slots=True)
class GuardResult:
    verdict: Verdict
    layer: str
    matched: str | None = None

    @property
    def blocked(self) -> bool:
        return self.verdict is not Verdict.ALLOW


# Questions that ask for a decision or a prognosis about the reader's own case.
_ADVICE_PATTERNS: dict[str, list[str]] = {
    "en": [
        r"\bshould i\b.*\b(object|appeal|contest|sign|pay|accept|refuse|complain|sue|ignore|respond|agree)",
        r"\b(do|must) i (really )?have to (pay|accept|move|leave|agree)",
        r"\b(is|was) (this|it|that) (legal|lawful|illegal|allowed|valid|correct|right)\b",
        r"\bcan (they|the \w+|my landlord|the office) (really )?(do|demand|ask|charge|evict|deport)",
        r"\b(my|our) chances\b|\bwill i win\b|\bwin (the|this|my) (case|appeal)",
        r"\b(is|would) (an? )?(objection|appeal|complaint|lawsuit) (worth|make sense|succeed)",
        r"\bwhat (would|should) (you|i) (do|write)\b.*\b(object|appeal|case|landlord|office)",
        r"\bwrite (me )?(an? )?(objection|appeal|widerspruch|einspruch)\b",

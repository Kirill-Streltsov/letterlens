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



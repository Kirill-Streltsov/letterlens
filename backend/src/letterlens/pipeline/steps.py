"""Pipeline steps. Each step is a pure function of (state, deps) -> state.

The same functions run in-process (local development, tests) and inside the
Step Functions worker Lambda (production). Steps never log letter text.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from letterlens.domain import (
    Citation,
    Explanation,
    ExplanationDraft,
    Extraction,
    LetterType,
    NextStep,
    Passage,
    SummarySentence,
    VerifiedFacts,
)
from letterlens.extraction.rules import extract_with_rules

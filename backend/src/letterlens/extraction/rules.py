"""Rule-based extractor.

Three roles:
1. Degraded mode: the pipeline uses it when the LLM budget is spent or every
   provider fails. Results then carry the flag ``degraded``.
2. Baseline: the evaluation compares the LLM extractor against it.
3. Offline provider: local development and tests run without an API key.
"""

from __future__ import annotations

import re

from letterlens.domain import (
    ExtractedAction,
    ExtractedAmount,
    ExtractedDate,
    ExtractedDeadline,
    ExtractedReference,
    ExtractedText,
    Extraction,
    LetterDocument,
)
from letterlens.grounding.deadlines import parse_relative_period
from letterlens.grounding.german import find_amounts, find_dates, normalize


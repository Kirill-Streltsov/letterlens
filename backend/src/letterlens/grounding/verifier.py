"""Grounding check: every date and amount must occur in its cited source line.

Rule: a value that this module cannot find in the cited line is never shown
as a fact. It gets the state NEEDS_CHECK and a note for the reader.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from letterlens.domain import (
    ExtractedDeadline,
    Extraction,
    FactStatus,
    LetterDocument,
    OcrLine,
    VerifiedAmount,
    VerifiedDeadline,
    VerifiedFacts,
)
from letterlens.grounding.deadlines import estimate_deadline, parse_relative_period
from letterlens.grounding.german import (
    find_amounts,
    find_dates,
    parse_decimal_value,
    parse_iso_date,
)


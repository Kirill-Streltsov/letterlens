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

NOTE_NOT_IN_SOURCE = "This value was not found in the quoted line. Please check the original."
NOTE_OTHER_LINE = "This value appears in the letter, but not in the quoted line. Please check."
NOTE_ESTIMATE = "Estimated from the period in the letter. Please check the exact date."
NOTE_NO_LETTER_DATE = "The letter date is unknown, so the end of the period cannot be estimated."
NOTE_BEFORE_LETTER = "This date is before the letter date. Please check."

_LETTER_DATE_HINTS = ("datum", "den ", "vom ")
_HEADER_LINES = 20


def _valid_ids(ids: list[str], lines: dict[str, OcrLine]) -> list[str]:
    return [i for i in dict.fromkeys(ids) if i in lines]


def _text(ids: list[str], lines: dict[str, OcrLine]) -> str:
    return "\n".join(lines[i].text for i in ids)



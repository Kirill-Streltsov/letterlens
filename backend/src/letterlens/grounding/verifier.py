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


def _verify_letter_date(
    extraction: Extraction, doc: LetterDocument, lines: dict[str, OcrLine]
) -> tuple[date | None, FactStatus]:
    proposed = parse_iso_date(extraction.letter_date.value)
    ids = _valid_ids(extraction.letter_date.line_ids, lines)
    if proposed is not None and proposed in find_dates(_text(ids, lines)):
        return proposed, FactStatus.VERIFIED
    # Fallback: a header line with a date hint, for example "Datum: 03.11.2026".
    for line in doc.lines[:_HEADER_LINES]:
        lowered = line.text.lower()
        dates = find_dates(line.text)
        if dates and any(hint in lowered for hint in _LETTER_DATE_HINTS):
            return dates[0], FactStatus.NEEDS_CHECK
    return proposed, FactStatus.NEEDS_CHECK


def _verify_deadline(
    idx: int,
    item: ExtractedDeadline,
    letter_date: date | None,
    doc_dates: set[date],
    lines: dict[str, OcrLine],
) -> VerifiedDeadline:
    ids = _valid_ids(item.line_ids, lines)
    cited = _text(ids, lines)
    common = {
        "id": f"d{idx}",
        "description": item.description.strip()[:300],
        "line_ids": ids,
        "source_text": cited or None,
    }

    explicit = parse_iso_date(item.date) if item.kind != "relative" else None
    if explicit is not None:
        if explicit in find_dates(cited):
            status, note = FactStatus.VERIFIED, None
        elif explicit in doc_dates:
            status, note = FactStatus.NEEDS_CHECK, NOTE_OTHER_LINE
        else:
            status, note = FactStatus.NEEDS_CHECK, NOTE_NOT_IN_SOURCE
        if letter_date is not None and explicit < letter_date:
            status, note = FactStatus.NEEDS_CHECK, NOTE_BEFORE_LETTER
        return VerifiedDeadline(
            due_date=explicit, status=status, is_estimate=False, note=note, **common
        )

    # Relative deadline: the period text must be in the cited line.
    period = parse_relative_period(cited) or (
        parse_relative_period(item.relative_expression or "") if not cited else None
    )
    if period is None:
        return VerifiedDeadline(
            due_date=None,
            status=FactStatus.NEEDS_CHECK,
            is_estimate=True,
            note=NOTE_NOT_IN_SOURCE,
            **common,
        )
    if letter_date is None:
        return VerifiedDeadline(
            due_date=None,
            status=FactStatus.NEEDS_CHECK,
            is_estimate=True,
            note=NOTE_NO_LETTER_DATE,
            **common,
        )
    estimate = estimate_deadline(period, letter_date)
    return VerifiedDeadline(
        due_date=estimate.due_date,
        status=FactStatus.NEEDS_CHECK,
        is_estimate=True,
        rule=estimate.rule,
        note=NOTE_ESTIMATE,
        **common,
    )


def verify(extraction: Extraction, doc: LetterDocument) -> VerifiedFacts:
    lines = doc.line_map()
    doc_dates = set(find_dates(doc.plain_text()))
    doc_amounts = set(find_amounts(doc.plain_text()))
    letter_date, letter_date_status = _verify_letter_date(extraction, doc, lines)

    deadlines: list[VerifiedDeadline] = []
    seen_deadlines: set[tuple[object, str]] = set()
    for item in extraction.deadlines:
        verified = _verify_deadline(len(deadlines) + 1, item, letter_date, doc_dates, lines)
        key = (verified.due_date, ",".join(verified.line_ids))
        if key in seen_deadlines:
            continue
        seen_deadlines.add(key)
        deadlines.append(verified)

    amounts: list[VerifiedAmount] = []
    seen_amounts: set[tuple[Decimal, str]] = set()
    for item in extraction.amounts:
        value = parse_decimal_value(item.value)
        if value is None:
            continue
        ids = _valid_ids(item.line_ids, lines)
        if value in find_amounts(_text(ids, lines)):
            status, note = FactStatus.VERIFIED, None
        elif value in doc_amounts:
            status, note = FactStatus.NEEDS_CHECK, NOTE_OTHER_LINE

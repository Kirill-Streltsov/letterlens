"""Grounding check: every date and amount must occur in its cited source line.

Rule: a value that this module cannot find in the cited line is never shown
as a fact. It gets the state NEEDS_CHECK and a note for the reader.
"""

from __future__ import annotations

import re
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
from letterlens.extraction.rules import is_internal_document
from letterlens.grounding.deadlines import estimate_deadline, parse_relative_period
from letterlens.grounding.german import (
    find_dates,
    find_money_numbers,
    parse_decimal_value,
    parse_iso_date,
)

NOTE_NOT_IN_SOURCE = "This value was not found in the quoted line. Please check the original."
NOTE_OTHER_LINE = "This value appears in the letter, but not in the quoted line. Please check."
NOTE_ESTIMATE = "Estimated from the period in the letter. Please check the exact date."
NOTE_NO_LETTER_DATE = "The letter date is unknown, so the end of the period cannot be estimated."
NOTE_BEFORE_LETTER = "This date is before the letter date. Please check."
NOTE_NO_DATE = (
    "The letter names a deadline, but no date for it was found in the letter. Please check the original."
)
NOTE_DELIVERY = (
    "The period starts on the delivery date that is written on the envelope (formal delivery). "
    "This estimate uses the letter date. Please check the envelope."
)
_DELIVERY = re.compile(r"\bzustellung\b|\bzugestellt\b", re.IGNORECASE)
# Lines that state an assessed total or an amount already withheld or paid. OCR often garbles
# "festgesetzt werden" (for example "restgesetzt weraen"), so the first letter is not checked.
_ASSESSED_LINE = re.compile(
    r"\w?estgesetzt\s+wer\w*|ab\s+steuerabzug|bereits\s+gezahlt|anzurechnen|geleistete\s+vorauszahlung",
    re.IGNORECASE,
)

# Whole words only: "den" must not match inside "Studierenden".
_LETTER_DATE_HINT = re.compile(r"\b(?:datum|den|vom)\b", re.IGNORECASE)
_HEADER_LINES = 20
_PLACE_DATE = re.compile(r"^[A-ZÄÖÜ][\wäöüß .-]{1,40},\s*\d{1,2}\.")


def _valid_ids(ids: list[str], lines: dict[str, OcrLine]) -> list[str]:
    return [i for i in dict.fromkeys(ids) if i in lines]


def _text(ids: list[str], lines: dict[str, OcrLine]) -> str:
    return "\n".join(lines[i].text for i in ids)


def _verify_letter_date(
    extraction: Extraction, doc: LetterDocument, lines: dict[str, OcrLine]
) -> tuple[date | None, FactStatus]:
    proposed = parse_iso_date(extraction.letter_date.value)
    ids = _valid_ids(extraction.letter_date.line_ids, lines)
    doc_dates = set(find_dates("\n".join(line.text for line in lines.values())))
    if proposed is not None and proposed in find_dates(_text(ids, lines)):
        return proposed, FactStatus.VERIFIED
    # Fallback: a header line with a date hint, for example "Datum: 03.11.2026".
    for line in doc.lines[:_HEADER_LINES]:
        lowered = line.text.lower()
        dates = find_dates(line.text)
        if dates and (_LETTER_DATE_HINT.search(lowered) or _PLACE_DATE.match(line.text)):
            return dates[0], FactStatus.NEEDS_CHECK
    # A date that is nowhere in the letter is not shown, not even as "please check".
    return (proposed if proposed in doc_dates else None), FactStatus.NEEDS_CHECK


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
    if explicit is not None and explicit not in doc_dates:
        # The model wrote a date that is nowhere in the letter, for example "bis zum TT.MM.2015"
        # read as a real date, or a period it computed itself. Never show it. If the cited line
        # names a period, estimate it with the documented rule instead.
        if parse_relative_period(cited) is None:
            return VerifiedDeadline(
                due_date=None, status=FactStatus.NEEDS_CHECK, is_estimate=False, note=NOTE_NO_DATE, **common
            )
        explicit = None
    if explicit is not None:
        if explicit in find_dates(cited):
            status, note = FactStatus.VERIFIED, None
        elif explicit in doc_dates:
            status, note = FactStatus.NEEDS_CHECK, NOTE_OTHER_LINE
        else:
            status, note = FactStatus.NEEDS_CHECK, NOTE_NOT_IN_SOURCE
        if letter_date is not None and explicit < letter_date:
            status, note = FactStatus.NEEDS_CHECK, NOTE_BEFORE_LETTER
        return VerifiedDeadline(due_date=explicit, status=status, is_estimate=False, note=note, **common)

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
        note=NOTE_DELIVERY if _DELIVERY.search(cited) else NOTE_ESTIMATE,
        **common,
    )


def verify(extraction: Extraction, doc: LetterDocument) -> VerifiedFacts:
    from letterlens.safety.guardrail import neutralize_injections

    # Lines that look like instructions to a model are never a valid source.
    _, suspicious = neutralize_injections(doc)
    lines = {k: v for k, v in doc.line_map().items() if k not in suspicious}
    trusted_text = "\n".join(line.text for line in lines.values())
    doc_dates = set(find_dates(trusted_text))
    doc_amounts = set(find_money_numbers(trusted_text))
    letter_date, letter_date_status = _verify_letter_date(extraction, doc, lines)

    if is_internal_document(doc):
        # A staff circular names dates and tasks for employees. The model does not always see
        # this (live evaluation, November 2026), so the code removes them for every extractor.
        extraction = extraction.model_copy(update={"deadlines": [], "required_actions": []})

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
    for amt in extraction.amounts:
        value = parse_decimal_value(amt.value)
        if value is None:
            continue
        ids = _valid_ids(amt.line_ids, lines)
        if value in find_money_numbers(_text(ids, lines)):
            status, note = FactStatus.VERIFIED, None
        elif value in doc_amounts:
            status, note = FactStatus.NEEDS_CHECK, NOTE_OTHER_LINE
        else:
            # An amount that is nowhere in the letter (a blank "_ EUR" read as 0.00, a percentage
            # read as money, a sum the model computed) is not shown at all.
            continue
        direction = amt.direction if amt.direction in {"to_pay", "to_receive"} else "info"
        source_lines = [lines[i].text for i in ids if value in find_money_numbers(lines[i].text)]
        if direction == "to_pay" and source_lines and all(_ASSESSED_LINE.search(t) for t in source_lines):
            # An assessed total or a withheld amount is not a payment request. Saying "pay 52,112 EUR"
            # when 441 EUR are due would frighten the reader, so the code corrects the model here.
            direction = "info"
        amount_key = (value, direction)
        if amount_key in seen_amounts:
            continue
        seen_amounts.add(amount_key)
        amounts.append(
            VerifiedAmount(
                id=f"a{len(amounts) + 1}",
                value=value,
                currency=(amt.currency or "EUR").upper()[:3],
                direction=direction,
                status=status,
                description=amt.description.strip()[:300],
                line_ids=ids,
                note=note,
            )
        )

    checkable = [d for d in deadlines if not d.is_estimate] + amounts
    verified_count = sum(1 for f in checkable if f.status is FactStatus.VERIFIED)
    if extraction.letter_date.value:
        checkable_count = len(checkable) + 1
        verified_count += letter_date_status is FactStatus.VERIFIED
    else:
        checkable_count = len(checkable)
    rate = verified_count / checkable_count if checkable_count else 1.0

    return VerifiedFacts(
        sender=extraction.sender.model_copy(
            update={"line_ids": _valid_ids(extraction.sender.line_ids, lines)}
        ),
        subject=extraction.subject.model_copy(
            update={"line_ids": _valid_ids(extraction.subject.line_ids, lines)}
        ),
        letter_date=letter_date,
        letter_date_status=letter_date_status,
        reference_numbers=[
            r.model_copy(update={"line_ids": _valid_ids(r.line_ids, lines)})
            for r in extraction.reference_numbers
            if r.value.strip() and r.value in _text(_valid_ids(r.line_ids, lines), lines)
        ],
        deadlines=deadlines,
        amounts=amounts,
        required_actions=[
            a.model_copy(update={"line_ids": _valid_ids(a.line_ids, lines)})
            for a in extraction.required_actions
        ],
        grounding_rate=round(rate, 4),
    )

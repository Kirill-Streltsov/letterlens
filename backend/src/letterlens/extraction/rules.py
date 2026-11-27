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

_REF_LABELS = re.compile(
    r"(?P<label>Steuernummer|StNr\.?|Identifikationsnummer|BG-Nummer|Kundennummer|"
    r"Versichertennummer|Aktenzeichen|Az\.|Mieternummer|Vertragsnummer|Beitragsnummer|"
    r"Unser Zeichen|Kindergeld-Nr\.|Mietobjekt-Nr\.)\s*:?\s*(?P<value>\S.*)$",
    re.IGNORECASE,
)
# A deadline keyword followed closely by a date. "bis zu 140 Tage" (up to) is not a deadline.
_DUE = re.compile(
    r"\b(?:bis|spätestens|frist)\b(?:\s+(?:zum|zur|zu\s+dem|spätestens|am|ende))?[\s:,]{1,4}"
    r"(?:\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}|\d{1,2}\.\s+[A-Za-zÄÖÜäöü]+\.?\s+\d{4})",
    re.IGNORECASE,
)
_APPOINTMENT = re.compile(r"\b(termin|am\s.+\bum\s+\d{1,2}[:.]\d{2})", re.IGNORECASE)
_VALID_FROM = re.compile(r"\b(ab dem|ab|vom|gültig bis|für die zeit)\b", re.IGNORECASE)
# "Datum: 03.11.2026", "Bochum, den 03.11.2026", "Hagen, 12.10.2026", "Bochum, 30. Juni 2026"
_LETTER_DATE = re.compile(r"^(datum\b|.*,\s*den\b|[A-ZÄÖÜ][\wäöüß .-]{1,40},\s*\d{1,2}\.)", re.IGNORECASE)
# Assessed totals and amounts already withheld or paid are information, not a payment request.
_INFO = re.compile(
    r"festgesetzt\s+werden|ab\s+steuerabzug|bereits\s+gezahlt|geleistete\s+vorauszahlung", re.IGNORECASE
)
_TO_RECEIVE = re.compile(r"erstattung|guthaben|bewilligt|gesamtbetrag:?\s*$|monatlicher", re.IGNORECASE)
_TO_PAY = re.compile(
    r"zu wenig gezahlt|geldbuße|verwarnungsgeld|zahlen|überweisen|rückstand|nachzahlung|forderung|säumnis|gebühr|kosten|"
    r"zu erstatten|offen|gesamtbetrag|insgesamt|erhöhung|auf\s",
    re.IGNORECASE,
)
_ACTION = re.compile(r"^(bitte|reichen sie|senden sie|zahlen sie|bringen sie|überweisen sie)", re.IGNORECASE)
_RECEIPT_FORM = re.compile(r"gegen\s+empfangsbekenntnis|^empfangsbekenntnis\b", re.IGNORECASE)
# An internal document for staff (a circular or an instruction) has no deadlines for the reader.
_INTERNAL = re.compile(
    r"\b(?:rundbrief|rundschreiben|dienstanweisung|fachliche\s+weisung|"
    r"an\s+alle\s+(?:teams|mitarbeitenden|beschäftigten)|richtet\s+sich\s+an\s+die\s+mitarbeitenden)\b",
    re.IGNORECASE,
)
_SKIP_SUBJECT = re.compile(r"^(sehr geehrte|liebe|anbei|datum)", re.IGNORECASE)


def is_internal_document(doc: LetterDocument) -> bool:
    """True for a circular or an instruction for staff. Its dates and tasks are not the reader's."""
    return any(_INTERNAL.search(line.text) for line in doc.lines)


def extract_with_rules(doc: LetterDocument) -> Extraction:
    lines = doc.lines
    sender = ExtractedText(value=lines[0].text, line_ids=[lines[0].id])

    letter_date = ExtractedDate(value=None, line_ids=[])
    date_index = 0
    for i, line in enumerate(lines[:20]):
        dates = find_dates(line.text)
        if dates and _LETTER_DATE.match(normalize(line.text)):
            letter_date = ExtractedDate(value=dates[0].isoformat(), line_ids=[line.id])
            date_index = i
            break

    subject = ExtractedText(value=None, line_ids=[])
    for line in lines[date_index + 1 : date_index + 4]:
        if line.text.strip() and not _SKIP_SUBJECT.match(line.text):
            subject = ExtractedText(value=line.text.strip(), line_ids=[line.id])
            break

    references: list[ExtractedReference] = []
    for line in lines[:25]:
        if match := _REF_LABELS.search(line.text):
            label = match["label"].rstrip(".:")
            if label.lower().startswith("identifikation"):
                continue  # a tax ID is personal data, not a case reference
            references.append(
                ExtractedReference(label=label, value=match["value"].strip(), line_ids=[line.id])
            )

    deadlines: list[ExtractedDeadline] = []
    amounts: list[ExtractedAmount] = []
    actions: list[ExtractedAction] = []
    for i, line in enumerate(lines):
        text = line.text
        if i <= date_index and letter_date.value:
            continue
        dates = find_dates(text)
        if dates and _APPOINTMENT.search(text) and not _VALID_FROM.search(text):
            deadlines.append(
                ExtractedDeadline(
                    kind="explicit_date",
                    date=dates[0].isoformat(),
                    relative_expression=None,
                    description="Appointment",
                    line_ids=[line.id],
                )
            )
        elif dates and _DUE.search(text) and not _VALID_FROM.search(text):
            deadlines.append(
                ExtractedDeadline(
                    kind="explicit_date",
                    date=dates[-1].isoformat(),
                    relative_expression=None,
                    description="Due date",
                    line_ids=[line.id],
                )
            )
        elif period := parse_relative_period(text):
            deadlines.append(
                ExtractedDeadline(
                    kind="relative",
                    date=None,
                    relative_expression=f"{period.amount} {period.unit.value} ({period.anchor.value})",
                    description="Period for a reply or a legal remedy",
                    line_ids=[line.id],
                )
            )
        for value in find_amounts(text):
            if _INFO.search(text):
                direction = "info"
            elif _TO_RECEIVE.search(text):
                direction = "to_receive"
            elif _TO_PAY.search(text):
                direction = "to_pay"
            else:
                direction = "info"
            amounts.append(
                ExtractedAmount(
                    value=str(value),
                    currency="EUR",
                    description=text.strip()[:120],
                    direction=direction,
                    line_ids=[line.id],
                )
            )
        if _ACTION.match(text.strip()):
            actions.append(ExtractedAction(description=text.strip(), line_ids=[line.id]))
        elif _RECEIPT_FORM.search(text) and not any("acknowledgement" in a.description for a in actions):
            actions.append(
                ExtractedAction(
                    description="Sign and return the acknowledgement of receipt (Empfangsbekenntnis)",
                    line_ids=[line.id],
                )
            )

    if is_internal_document(doc):
        deadlines, actions = [], []
    return Extraction(
        sender=sender,
        subject=subject,
        letter_date=letter_date,
        reference_numbers=references,
        deadlines=deadlines,
        amounts=amounts,
        required_actions=actions,
    )

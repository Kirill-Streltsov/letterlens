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
_DUE = re.compile(r"\bbis\s+(zum|spätestens|zu)?\b|\bspätestens\b|\bfrist\b", re.IGNORECASE)
_APPOINTMENT = re.compile(r"\b(termin|am\s.+\bum\s+\d{1,2}[:.]\d{2})", re.IGNORECASE)
_VALID_FROM = re.compile(r"\b(ab dem|ab|vom|gültig bis|für die zeit)\b", re.IGNORECASE)
_LETTER_DATE = re.compile(r"^(datum|.*,\s*den)\b", re.IGNORECASE)
_TO_RECEIVE = re.compile(r"erstattung|guthaben|bewilligt|gesamtbetrag:?\s*$|monatlicher", re.IGNORECASE)
_TO_PAY = re.compile(
    r"zahlen|überweisen|rückstand|nachzahlung|forderung|säumnis|gebühr|kosten|"
    r"zu erstatten|offen|gesamtbetrag|insgesamt|erhöhung|auf\s",
    re.IGNORECASE,
)
_ACTION = re.compile(
    r"^(bitte|reichen sie|senden sie|zahlen sie|bringen sie|überweisen sie)", re.IGNORECASE
)
_SKIP_SUBJECT = re.compile(r"^(sehr geehrte|liebe|anbei|datum)", re.IGNORECASE)


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

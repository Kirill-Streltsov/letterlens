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



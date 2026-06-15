"""Deterministic parsers for German dates and money amounts.

These parsers are the source of truth for the grounding check. The LLM
proposes a value and a source line. This module decides whether the line
really contains that value.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

MONTHS: dict[str, int] = {
    "januar": 1, "jänner": 1, "jan": 1,
    "februar": 2, "feb": 2,
    "märz": 3, "maerz": 3, "marz": 3, "mär": 3, "mrz": 3,
    "april": 4, "apr": 4,
    "mai": 5,
    "juni": 6, "jun": 6,
    "juli": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "oktober": 10, "okt": 10,
    "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}  # fmt: skip

_MONTH_ALT = "|".join(sorted(MONTHS, key=len, reverse=True))

# 15.12.2026 | 15.12.26 | 15. 12. 2026 | 5.1.2027
_NUMERIC_DATE = re.compile(r"(?<!\d)(\d{1,2})\s?\.\s?(\d{1,2})\s?\.\s?(\d{4}|\d{2})(?!\d)")
# 15. Dezember 2026 | 15 Dez. 2026
_WORD_DATE = re.compile(
    rf"(?<!\d)(\d{{1,2}})\.?\s+({_MONTH_ALT})\.?\s+(\d{{4}})(?!\d)", re.IGNORECASE
)
# 2026-12-15
_ISO_DATE = re.compile(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)")

# 1.234,56 € | 1234,56 EUR | EUR 1.234,56 | 12 € | 1 234,56 Euro
_AMOUNT_NUMBER = r"\d{1,3}(?:[.\s  ]\d{3})+(?:,\d{1,2})?|\d+(?:,\d{1,2})?"
_CURRENCY = r"(?:€|EUR|Euro)"
_AMOUNT = re.compile(
    rf"(?:{_CURRENCY}\s?(?P<a>{_AMOUNT_NUMBER})(?:\s?€)?)|(?:(?P<b>{_AMOUNT_NUMBER})\s?{_CURRENCY})",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    """Normalize Unicode, whitespace and common OCR quirks for matching."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace(" ", " ").replace(" ", " ")
    return re.sub(r"\s+", " ", text).strip()


def _two_digit_year(year: int) -> int:
    return 2000 + year if year < 70 else 1900 + year


def find_dates(text: str) -> list[date]:
    """Return every valid calendar date written in ``text``, in order of appearance."""
    text = normalize(text)
    found: list[tuple[int, date]] = []
    for match in _NUMERIC_DATE.finditer(text):
        day, month, year_s = int(match[1]), int(match[2]), match[3]
        year = int(year_s) if len(year_s) == 4 else _two_digit_year(int(year_s))
        _append_date(found, match.start(), year, month, day)
    for match in _WORD_DATE.finditer(text):
        month = MONTHS[match[2].lower()]
        _append_date(found, match.start(), int(match[3]), month, int(match[1]))
    for match in _ISO_DATE.finditer(text):
        _append_date(found, match.start(), int(match[1]), int(match[2]), int(match[3]))
    found.sort(key=lambda item: item[0])
    return [d for _, d in found]


def _append_date(found: list[tuple[int, date]], pos: int, y: int, m: int, d: int) -> None:
    try:
        found.append((pos, date(y, m, d)))
    except ValueError:
        return


def parse_amount(raw: str) -> Decimal | None:
    """Parse a German-formatted number such as ``1.234,56`` into a Decimal."""
    cleaned = re.sub(r"[.\s  ]", "", raw).replace(",", ".")
    try:
        return Decimal(cleaned).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None



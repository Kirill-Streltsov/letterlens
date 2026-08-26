from datetime import date
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from letterlens.grounding.german import (
    find_amounts,
    find_dates,
    parse_decimal_value,
    parse_iso_date,
)
from letterlens.synthetic.generator import fmt_date, fmt_eur


def test_numeric_and_word_dates() -> None:
    text = "Bitte zahlen Sie bis zum 15.12.2026 oder spätestens am 3. Januar 2027."
    assert find_dates(text) == [date(2026, 12, 15), date(2027, 1, 3)]


def test_short_year_and_spaces() -> None:
    assert find_dates("Frist: 5. 1. 27") == [date(2027, 1, 5)]



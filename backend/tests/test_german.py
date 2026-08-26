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


def test_invalid_dates_are_ignored() -> None:
    assert find_dates("am 31.02.2026 und 44.01.2026") == []


def test_iso_dates() -> None:
    assert find_dates("due 2026-03-01") == [date(2026, 3, 1)]


def test_reference_numbers_are_not_dates() -> None:
    assert find_dates("Steuernummer 123/456/78901") == []


def test_amount_formats() -> None:
    text = "Nachzahlung: 1.234,56 €, Gebühr EUR 12,00 und 99 Euro, total 1 234,50 EUR"
    assert find_amounts(text) == [
        Decimal("1234.56"),
        Decimal("12.00"),
        Decimal("99.00"),
        Decimal("1234.50"),
    ]


def test_numbers_without_currency_are_not_amounts() -> None:
    assert find_amounts("Zimmer 203, Postfach 1234") == []


def test_parse_llm_values() -> None:
    assert parse_decimal_value("1234.5") == Decimal("1234.50")
    assert parse_decimal_value("1.234,56 €") == Decimal("1234.56")
    assert parse_decimal_value("abc") is None
    assert parse_iso_date("2026-12-01") == date(2026, 12, 1)
    assert parse_iso_date("01.12.2026") == date(2026, 12, 1)
    assert parse_iso_date(None) is None


@given(st.dates(min_value=date(2000, 1, 1), max_value=date(2069, 12, 31)), st.sampled_from([0, 1]))
def test_date_round_trip(d: date, style: int) -> None:
    assert find_dates(f"Frist bis zum {fmt_date(d, style)}.") == [d]


@given(
    st.decimals(min_value=Decimal("0.01"), max_value=Decimal("999999.99"), places=2),
    st.sampled_from([0, 1]),
)
def test_amount_round_trip(value: Decimal, style: int) -> None:
    assert find_amounts(f"Betrag: {fmt_eur(value, style)}") == [value]

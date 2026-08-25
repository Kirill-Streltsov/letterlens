from datetime import date

import pytest

from letterlens.grounding.deadlines import (
    Anchor,
    RelativePeriod,
    Unit,
    add_months,
    easter_sunday,
    estimate_deadline,
    is_working_day,
    nationwide_holidays,
    parse_relative_period,
)


@pytest.mark.parametrize(
    ("year", "expected"),
    [
        (2024, date(2024, 3, 31)),
        (2025, date(2025, 4, 20)),
        (2026, date(2026, 4, 5)),
        (2027, date(2027, 3, 28)),
    ],
)
def test_easter(year: int, expected: date) -> None:
    assert easter_sunday(year) == expected


def test_holidays_2026() -> None:
    h = nationwide_holidays(2026)
    assert date(2026, 4, 3) in h  # Good Friday
    assert date(2026, 5, 14) in h  # Ascension
    assert date(2026, 5, 25) in h  # Whit Monday
    assert date(2026, 10, 3) in h
    assert not is_working_day(date(2026, 12, 25))


def test_add_months_clamps_to_month_end() -> None:
    assert add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert add_months(date(2026, 11, 30), 3) == date(2027, 2, 28)
    assert add_months(date(2026, 12, 15), 1) == date(2027, 1, 15)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("innerhalb eines Monats nach Bekanntgabe", RelativePeriod(1, Unit.MONTHS, Anchor.NOTIFICATION)),
        ("binnen zwei Wochen nach Zugang", RelativePeriod(2, Unit.WEEKS, Anchor.NOTIFICATION)),
        ("innerhalb von 30 Tagen nach Erhalt", RelativePeriod(30, Unit.DAYS, Anchor.RECEIPT)),
        (
            "innerhalb von 14 Tagen ab Datum dieses Schreibens",
            RelativePeriod(14, Unit.DAYS, Anchor.LETTER_DATE),
        ),
    ],
)
def test_parse_relative_period(text: str, expected: RelativePeriod) -> None:
    assert parse_relative_period(f"Der Einspruch ist {text} einzulegen.") == expected


def test_no_period_in_plain_text() -> None:
    assert parse_relative_period("Bitte zahlen Sie bis zum 01.12.2026.") is None


def test_one_month_after_notification() -> None:
    # Letter dated Tue 2026-03-10 -> received Sat 03-14 -> next working day Mon 03-16
    # -> one month later Thu 2026-04-16.
    est = estimate_deadline(RelativePeriod(1, Unit.MONTHS, Anchor.NOTIFICATION), date(2026, 3, 10))
    assert est.start_date == date(2026, 3, 16)
    assert est.due_date == date(2026, 4, 16)


def test_end_on_holiday_moves_to_next_working_day() -> None:
    # Letter 2026-11-30 -> received Fri 12-04 -> plus 3 weeks = Fri 12-25 (holiday)
    # -> 12-26 holiday, 12-27 Sunday -> Mon 2026-12-28.
    est = estimate_deadline(RelativePeriod(3, Unit.WEEKS, Anchor.NOTIFICATION), date(2026, 11, 30))
    assert est.start_date == date(2026, 12, 4)
    assert est.due_date == date(2026, 12, 28)
    assert "moved from 2026-12-25" in est.rule


def test_letter_date_anchor() -> None:
    est = estimate_deadline(RelativePeriod(14, Unit.DAYS, Anchor.LETTER_DATE), date(2026, 6, 1))
    assert est.due_date == date(2026, 6, 15)

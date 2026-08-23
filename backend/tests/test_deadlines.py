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



"""Estimate the end date of relative deadlines in German official letters.

The result is always an *estimate*. The client shows it with the state
"please check" and the rule that produced it. The rules are general
information, not an assessment of an individual case:

* Notification fiction: a letter sent by post counts as received on the
  fourth day after posting (since 1 January 2025: § 122 (2) AO, § 37 (2)
  SGB X, § 41 (2) VwVfG). If that day is a Saturday, Sunday or public
  holiday, it moves to the next working day.
* Period end: a period in months ends on the day with the same number in
  the target month; if that day does not exist, on the last day of the
  month (§ 188 (2), (3) BGB). Periods in days or weeks are counted from
  the day after the start event (§ 187 (1) BGB).
* If the last day is a Saturday, Sunday or public holiday, the period ends
  on the next working day (§ 193 BGB, § 108 (3) AO).

Only nationwide public holidays are known here. Regional holidays are a
documented limitation, and a reason the date stays "please check".
"""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum

NOTIFICATION_FICTION_DAYS = 4


def easter_sunday(year: int) -> date:
    """Anonymous Gregorian algorithm (Meeus/Jones/Butcher)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    ell = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * ell) // 451
    month, day = divmod(h + ell - 7 * m + 114, 31)
    return date(year, month, day + 1)


def nationwide_holidays(year: int) -> frozenset[date]:
    easter = easter_sunday(year)
    return frozenset(
        {
            date(year, 1, 1),  # Neujahr
            easter - timedelta(days=2),  # Karfreitag
            easter + timedelta(days=1),  # Ostermontag
            date(year, 5, 1),  # Tag der Arbeit
            easter + timedelta(days=39),  # Christi Himmelfahrt
            easter + timedelta(days=50),  # Pfingstmontag
            date(year, 10, 3),  # Tag der Deutschen Einheit
            date(year, 12, 25),
            date(year, 12, 26),
        }
    )


def is_working_day(day: date) -> bool:
    return day.weekday() < 5 and day not in nationwide_holidays(day.year)


def next_working_day(day: date) -> date:
    while not is_working_day(day):
        day += timedelta(days=1)
    return day



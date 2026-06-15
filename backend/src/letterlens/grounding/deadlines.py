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


def add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(start.day, last_day))


class Unit(StrEnum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"


class Anchor(StrEnum):
    NOTIFICATION = "notification"  # "nach Bekanntgabe", "nach Zugang", "nach Zustellung"
    LETTER_DATE = "letter_date"  # "ab Datum dieses Schreibens"
    RECEIPT = "receipt"  # "nach Erhalt"


@dataclass(frozen=True, slots=True)
class RelativePeriod:
    amount: int
    unit: Unit
    anchor: Anchor


_NUMBER_WORDS: dict[str, int] = {
    "einem": 1, "einer": 1, "eines": 1, "ein": 1, "eine": 1,
    "zwei": 2, "drei": 3, "vier": 4, "fünf": 5, "sechs": 6, "sieben": 7,
    "acht": 8, "zehn": 10, "zwölf": 12, "vierzehn": 14, "einundzwanzig": 21,
    "dreißig": 30, "dreissig": 30,
}  # fmt: skip

_UNIT_WORDS: dict[str, Unit] = {
    "tag": Unit.DAYS, "tage": Unit.DAYS, "tagen": Unit.DAYS, "tages": Unit.DAYS,
    "woche": Unit.WEEKS, "wochen": Unit.WEEKS,
    "monat": Unit.MONTHS, "monats": Unit.MONTHS, "monate": Unit.MONTHS, "monaten": Unit.MONTHS,
}  # fmt: skip

_PERIOD = re.compile(
    r"(?:innerhalb|binnen|in(?:nerhalb)?\s+einer\s+frist\s+von|frist\s+von)\s+"
    r"(?:von\s+)?(?P<num>\d{1,3}|" + "|".join(_NUMBER_WORDS) + r")\s+"
    r"(?P<unit>" + "|".join(_UNIT_WORDS) + r")\b",
    re.IGNORECASE,
)
_ANCHOR_NOTIFICATION = re.compile(r"bekanntgabe|zugang|zustellung", re.IGNORECASE)
_ANCHOR_RECEIPT = re.compile(r"erhalt|eingang", re.IGNORECASE)
_ANCHOR_LETTER = re.compile(r"datum|ab\s+heute|dieses\s+schreibens", re.IGNORECASE)


def parse_relative_period(text: str) -> RelativePeriod | None:
    """Find a period like ``innerhalb eines Monats nach Bekanntgabe`` in ``text``."""
    match = _PERIOD.search(text)
    if match is None:
        return None
    raw_num = match["num"].lower()
    amount = int(raw_num) if raw_num.isdigit() else _NUMBER_WORDS[raw_num]
    unit = _UNIT_WORDS[match["unit"].lower()]
    tail = text[match.end() : match.end() + 80]
    if _ANCHOR_NOTIFICATION.search(tail):
        anchor = Anchor.NOTIFICATION
    elif _ANCHOR_RECEIPT.search(tail):
        anchor = Anchor.RECEIPT
    elif _ANCHOR_LETTER.search(tail):
        anchor = Anchor.LETTER_DATE
    else:
        anchor = Anchor.NOTIFICATION
    return RelativePeriod(amount=amount, unit=unit, anchor=anchor)


@dataclass(frozen=True, slots=True)
class DeadlineEstimate:
    due_date: date
    start_date: date
    rule: str



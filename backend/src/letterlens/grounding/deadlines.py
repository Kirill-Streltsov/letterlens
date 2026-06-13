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


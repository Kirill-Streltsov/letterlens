"""Synthetic German official letters with exact ground-truth labels.

All names, addresses and numbers are invented. The generator is
deterministic for a given seed, so the golden set is reproducible.

Each template family has phrase variants. The evaluation splits by
template family, so classifier scores measure generalization to unseen
layouts, not memorized templates.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from letterlens.domain import LetterType

# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------


@dataclass
class DeadlineLabel:
    kind: str  # explicit_date | relative | appointment
    date: str | None = None
    relative_expression: str | None = None


@dataclass
class AmountLabel:
    value: str
    direction: str  # to_pay | to_receive | info


@dataclass
class SyntheticLetter:
    id: str
    letter_type: str
    template_id: str
    lines: list[str]
    sender: str
    letter_date: str
    references: dict[str, str]
    deadlines: list[DeadlineLabel] = field(default_factory=list)
    amounts: list[AmountLabel] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# --------------------------------------------------------------------------
# Random building blocks
# --------------------------------------------------------------------------

RECIPIENTS = [
    "Ayşe Yılmaz", "Olena Kovalenko", "Ahmad Al-Hassan", "Maria Popescu", "Jan Nowak",
    "Fatima Rahimi", "Dmytro Shevchenko", "Mehmet Demir", "Lina Haddad", "Svetlana Ivanova",
    "Kwame Mensah", "Elif Kaya", "Oksana Bondarenko", "Yusuf Öztürk", "Nour Khalil",
]  # fmt: skip
STREETS = [
    "Hauptstraße", "Bergstraße", "Kirchweg", "Am Stadtpark", "Lindenallee", "Bahnhofstraße",
    "Gartenstraße", "Schillerstraße", "Rosenweg", "Herner Straße", "Dorstener Straße",
]  # fmt: skip
CITIES = [
    ("44787", "Bochum"), ("44135", "Dortmund"), ("45127", "Essen"), ("45879", "Gelsenkirchen"),
    ("47051", "Duisburg"), ("44623", "Herne"), ("45468", "Mülheim an der Ruhr"),
]  # fmt: skip
MONTH_NAMES = [
    "Januar", "Februar", "März", "April", "Mai", "Juni", "Juli", "August",
    "September", "Oktober", "November", "Dezember",
]  # fmt: skip



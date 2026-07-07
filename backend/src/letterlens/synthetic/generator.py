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


class Rand:
    def __init__(self, seed: int) -> None:
        self.r = random.Random(seed)

    def pick[T](self, items: list[T]) -> T:
        return self.r.choice(items)

    def digits(self, n: int) -> str:
        return "".join(str(self.r.randint(0, 9)) for _ in range(n))

    def amount(self, low: int, high: int) -> Decimal:
        cents = self.r.choice([0, 0, 50, self.r.randint(1, 99)])
        return Decimal(f"{self.r.randint(low, high)}.{cents:02d}")

    def letter_date(self) -> date:
        return date(2026, 1, 5) + timedelta(days=self.r.randint(0, 330))

    def address(self) -> tuple[str, str, str]:
        plz, city = self.pick(CITIES)
        return (
            self.pick(RECIPIENTS),
            f"{self.pick(STREETS)} {self.r.randint(1, 120)}{self.pick(['', '', 'a', 'b'])}",
            f"{plz} {city}",
        )


def fmt_date(d: date, style: int = 0) -> str:
    if style == 1:
        return f"{d.day}. {MONTH_NAMES[d.month - 1]} {d.year}"
    return f"{d.day:02d}.{d.month:02d}.{d.year}"


def fmt_eur(value: Decimal, style: int = 0) -> str:
    whole, cents = f"{value:.2f}".split(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    if style == 1:
        return f"{grouped},{cents} EUR"
    return f"{grouped},{cents} €"


def working_after(d: date, days: int) -> date:
    out = d + timedelta(days=days)
    while out.weekday() >= 5:
        out += timedelta(days=1)
    return out


@dataclass
class Ctx:
    rnd: Rand
    letter_date: date
    recipient: tuple[str, str, str]
    date_style: int
    money_style: int

    def d(self, value: date) -> str:
        return fmt_date(value, self.date_style)

    def m(self, value: Decimal) -> str:
        return fmt_eur(value, self.money_style)


Built = tuple[list[str], str, dict[str, str], list[DeadlineLabel], list[AmountLabel]]


def _header(ctx: Ctx, sender_lines: list[str], ref_lines: list[str]) -> list[str]:
    name, street, city = ctx.recipient
    place = sender_lines[-1].split(" ", 1)[-1] if sender_lines else ""
    date_line = ctx.rnd.pick(
        [
            f"Datum: {ctx.d(ctx.letter_date)}",
            f"{place}, den {ctx.d(ctx.letter_date)}",
            f"Datum {ctx.d(ctx.letter_date)}",
        ]
    )
    return [*sender_lines, "", name, street, city, "", *ref_lines, date_line, ""]



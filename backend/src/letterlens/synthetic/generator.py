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


RELATIVE_OBJECTION = [
    "innerhalb eines Monats nach Bekanntgabe",
    "binnen eines Monats nach Bekanntgabe",
    "innerhalb eines Monats nach Zugang",
]


# --------------------------------------------------------------------------
# Templates: TAX
# --------------------------------------------------------------------------


def tax_assessment(ctx: Ctx) -> Built:
    r = ctx.rnd
    office = r.pick(["Bochum-Mitte", "Dortmund-Ost", "Essen-Süd", "Gelsenkirchen", "Herne"])
    sender = f"Finanzamt {office}"
    stnr = f"{r.digits(3)}/{r.digits(3)}/{r.digits(5)}"
    idnr = f"{r.digits(2)} {r.digits(3)} {r.digits(3)} {r.digits(3)}"
    year = ctx.letter_date.year - 1
    refund = r.r.random() < 0.4
    amount = r.amount(80, 3400)
    due = working_after(ctx.letter_date, 33)
    rel = r.pick(RELATIVE_OBJECTION)
    lines = _header(
        ctx,
        [sender, f"Postfach {r.digits(4)}", "44701 Bochum"],
        [f"Steuernummer: {stnr}", f"Identifikationsnummer: {idnr}"],
    )
    lines += [f"Bescheid für {year} über Einkommensteuer", ""]
    lines += [f"Die Steuer wird für das Kalenderjahr {year} festgesetzt.", ""]
    deadlines: list[DeadlineLabel] = []
    amounts: list[AmountLabel] = []
    if refund:
        lines += [
            f"Erstattung: {ctx.m(amount)}",
            "Der Betrag wird auf Ihr angegebenes Konto überwiesen.",
        ]
        amounts.append(AmountLabel(str(amount), "to_receive"))
    else:
        lines += [
            f"Nachzahlung: {ctx.m(amount)}",
            f"Bitte zahlen Sie den Betrag bis zum {ctx.d(due)}.",
            "Bei verspäteter Zahlung entstehen Säumniszuschläge.",
        ]
        amounts.append(AmountLabel(str(amount), "to_pay"))
        deadlines.append(DeadlineLabel("explicit_date", date=due.isoformat()))
    lines += [
        "",
        "Rechtsbehelfsbelehrung",
        "Der Bescheid kann mit dem Einspruch angefochten werden.",
        f"Der Einspruch ist {rel} dieses Bescheids",
        f"bei dem Finanzamt {office} schriftlich oder elektronisch einzulegen.",
        "",
        "Mit freundlichen Grüßen",
        "Ihr Finanzamt",
    ]
    deadlines.append(DeadlineLabel("relative", relative_expression=rel))
    return lines, sender, {"Steuernummer": stnr}, deadlines, amounts


def tax_reminder(ctx: Ctx) -> Built:
    r = ctx.rnd
    office = r.pick(["Duisburg-West", "Bochum-Süd", "Dortmund-Unna", "Mülheim an der Ruhr"])
    sender = f"Finanzamt {office}"
    stnr = f"{r.digits(3)}/{r.digits(4)}/{r.digits(4)}"
    year = ctx.letter_date.year - 1
    due = working_after(ctx.letter_date, r.pick([14, 21, 28]))
    lines = _header(ctx, [sender, f"{r.pick(STREETS)} {r.r.randint(1, 60)}"], [f"StNr. {stnr}"])
    lines += [
        r.pick(
            [
                f"Erinnerung: Abgabe der Einkommensteuererklärung {year}",
                f"Aufforderung zur Abgabe der Steuererklärung für {year}",
            ]
        ),
        "",
        "Sehr geehrte Damen und Herren,",
        f"Ihre Einkommensteuererklärung für {year} liegt uns noch nicht vor.",
        f"Bitte reichen Sie die Erklärung bis zum {ctx.d(due)} ein.",
        "Wenn Sie die Frist nicht einhalten, kann ein Verspätungszuschlag festgesetzt werden.",
        "Die Erklärung können Sie kostenlos über ELSTER übermitteln.",
        "",
        "Mit freundlichen Grüßen",
        "Im Auftrag",
    ]
    return lines, sender, {"Steuernummer": stnr}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], []


def tax_arrears(ctx: Ctx) -> Built:
    r = ctx.rnd
    office = r.pick(["Herne", "Gelsenkirchen-Nord", "Essen-NordOst"])
    sender = f"Finanzamt {office} - Erhebungsstelle"
    stnr = f"{r.digits(3)}/{r.digits(3)}/{r.digits(5)}"
    principal = r.amount(150, 2500)
    surcharge = (principal * Decimal("0.01") * r.r.randint(1, 4)).quantize(Decimal("1"))
    total = principal + surcharge
    due = working_after(ctx.letter_date, r.pick([7, 10, 14]))
    lines = _header(ctx, [sender, f"Postfach {r.digits(4)}"], [f"Steuernummer {stnr}"])
    lines += [
        "Mahnung",
        "",
        "Folgende Beträge sind trotz Fälligkeit noch nicht bezahlt:",
        f"Einkommensteuer: {ctx.m(principal)}",
        f"Säumniszuschläge: {ctx.m(surcharge)}",
        f"Gesamtbetrag: {ctx.m(total)}",
        "",
        f"Bitte überweisen Sie den Gesamtbetrag bis zum {ctx.d(due)}.",
        "Andernfalls müssen wir Vollstreckungsmaßnahmen einleiten.",
        "",
        "Mit freundlichen Grüßen",
    ]
    return lines, sender, {"Steuernummer": stnr}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], [
        AmountLabel(str(principal), "to_pay"),
        AmountLabel(str(surcharge), "to_pay"),
        AmountLabel(str(total), "to_pay"),
    ]


# --------------------------------------------------------------------------
# Templates: BENEFITS
# --------------------------------------------------------------------------


REFORM_DATE = date(2026, 7, 1)


def benefit_name(ctx: Ctx) -> str:
    """Bürgergeld became Grundsicherungsgeld on 1 July 2026 (SGB II reform)."""
    return "Grundsicherungsgeld" if ctx.letter_date >= REFORM_DATE else "Bürgergeld"


def jobcenter_approval(ctx: Ctx) -> Built:
    r = ctx.rnd
    city = r.pick(["Bochum", "Dortmund", "Essen", "Gelsenkirchen", "Herne"])
    sender = f"Jobcenter {city}"
    bg = f"{r.digits(5)}BG{r.digits(7)}"
    monthly = r.amount(560, 1900)
    start = (ctx.letter_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    end = (start + timedelta(days=180)).replace(day=1) - timedelta(days=1)
    rel = r.pick(RELATIVE_OBJECTION)
    lines = _header(
        ctx,
        [sender, f"{r.pick(STREETS)} {r.r.randint(1, 90)}"],
        [f"BG-Nummer: {bg}", f"Kundennummer: {r.digits(3)}D{r.digits(6)}"],
    )
    lines += [
        "Bescheid über die Bewilligung von Leistungen zur Sicherung des Lebensunterhalts",
        f"({benefit_name(ctx)})",
        "",
        f"für die Zeit vom {ctx.d(start)} bis {ctx.d(end)} werden Ihnen Leistungen bewilligt.",
        f"Monatlicher Gesamtbetrag: {ctx.m(monthly)}",
        "Änderungen in Ihren Verhältnissen müssen Sie unverzüglich mitteilen.",
        "",
        "Rechtsbehelfsbelehrung",
        f"Gegen diesen Bescheid kann {rel} Widerspruch erhoben werden.",
        f"Der Widerspruch ist schriftlich oder zur Niederschrift beim Jobcenter {city} einzulegen.",
    ]
    return lines, sender, {"BG-Nummer": bg}, [
        DeadlineLabel("relative", relative_expression=rel)
    ], [AmountLabel(str(monthly), "to_receive")]


def jobcenter_documents(ctx: Ctx) -> Built:
    r = ctx.rnd
    city = r.pick(["Duisburg", "Mülheim an der Ruhr", "Bochum", "Dortmund"])
    sender = f"Jobcenter {city}"
    bg = f"{r.digits(5)}BG{r.digits(7)}"
    due = working_after(ctx.letter_date, r.pick([14, 14, 21]))
    docs = r.r.sample(
        [
            "Kontoauszüge der letzten drei Monate",
            "aktuelle Lohnabrechnung",
            "Mietvertrag und aktuelle Mietbescheinigung",
            "Nachweis über den Bezug von Kindergeld",
            "Bescheinigung der Krankenkasse",
        ],
        3,
    )
    lines = _header(ctx, [sender, "Team 451"], [f"BG-Nummer {bg}"])
    lines += [
        r.pick(["Aufforderung zur Mitwirkung", "Anforderung von Unterlagen"]),
        "",
        "Sehr geehrte Damen und Herren,",
        "für die Prüfung Ihres Anspruchs benötigen wir folgende Unterlagen:",
        *[f"- {d}" for d in docs],
        f"Bitte reichen Sie die Unterlagen bis zum {ctx.d(due)} ein.",
        "Wenn Sie nicht mitwirken, können die Leistungen ganz oder teilweise versagt werden",
        "(§§ 60, 66 Erstes Buch Sozialgesetzbuch).",
        "",
        "Mit freundlichen Grüßen",
    ]
    return lines, sender, {"BG-Nummer": bg}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], []


def jobcenter_invitation(ctx: Ctx) -> Built:
    r = ctx.rnd
    city = r.pick(["Essen", "Herne", "Gelsenkirchen"])
    sender = f"Jobcenter {city}"
    appt = working_after(ctx.letter_date, r.pick([8, 10, 12]))
    time = r.pick(["08:30", "09:15", "10:00", "11:30", "13:45"])
    lines = _header(
        ctx,
        [sender, "Arbeitsvermittlung"],
        [f"Kundennummer: {r.digits(3)}D{r.digits(6)}"],
    )
    lines += [
        "Einladung",
        "",
        "Sehr geehrte Damen und Herren,",
        "bitte kommen Sie zu einem Gespräch über Ihre berufliche Situation",
        f"am {ctx.d(appt)} um {time} Uhr, Zimmer {r.r.randint(100, 420)}.",
        "Bringen Sie bitte Ihren Lebenslauf und Ihren Ausweis mit.",
        f"Wenn Sie ohne wichtigen Grund nicht kommen, kann Ihr {benefit_name(ctx)} gemindert werden.",
        "Können Sie den Termin nicht wahrnehmen, informieren Sie uns bitte vorher.",
    ]
    return lines, sender, {}, [DeadlineLabel("appointment", date=appt.isoformat())], []


def familienkasse_refund(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = "Familienkasse Nordrhein-Westfalen West"
    kg = f"{r.digits(3)}FK{r.digits(6)}"
    amount = r.amount(255, 1530)
    due = working_after(ctx.letter_date, 30)
    rel = r.pick(RELATIVE_OBJECTION)
    lines = _header(ctx, [sender, "Postfach 10 08 51", "45008 Essen"], [f"Kindergeld-Nr.: {kg}"])
    lines += [
        "Aufhebung der Festsetzung des Kindergeldes und Rückforderung",
        "",
        "Die Festsetzung des Kindergeldes wird aufgehoben, weil die Voraussetzungen",
        "nicht mehr vorliegen.",
        f"Das zu Unrecht gezahlte Kindergeld in Höhe von {ctx.m(amount)} ist zu erstatten.",
        f"Bitte überweisen Sie den Betrag bis zum {ctx.d(due)}.",
        "",
        "Rechtsbehelfsbelehrung",
        f"Gegen diesen Bescheid kann {rel} Einspruch eingelegt werden.",
    ]
    return lines, sender, {"Kindergeld-Nr.": kg}, [
        DeadlineLabel("explicit_date", date=due.isoformat()),
        DeadlineLabel("relative", relative_expression=rel),
    ], [AmountLabel(str(amount), "to_pay")]


# --------------------------------------------------------------------------
# Templates: HEALTH INSURANCE
# --------------------------------------------------------------------------

INSURERS = ["AOK NordWest", "Techniker Krankenkasse", "BARMER", "DAK-Gesundheit", "IKK classic"]


def insurance_arrears(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(INSURERS)
    kvnr = f"{r.pick(['A', 'K', 'M', 'T'])}{r.digits(9)}"
    principal = r.amount(90, 1200)
    fee = r.amount(1, 40)
    total = principal + fee
    due = working_after(ctx.letter_date, r.pick([10, 14]))
    lines = _header(ctx, [sender, "Beitragseinzug"], [f"Versichertennummer: {kvnr}"])
    lines += [
        "Zahlungserinnerung - Beitragsrückstand",
        "",
        f"Für Ihre freiwillige Versicherung besteht ein Rückstand von {ctx.m(principal)}.",
        f"Zusätzlich wurden Säumniszuschläge von {ctx.m(fee)} berechnet.",
        f"Bitte zahlen Sie insgesamt {ctx.m(total)} bis zum {ctx.d(due)}.",
        "Bei weiterem Zahlungsverzug ruht Ihr Leistungsanspruch teilweise.",
        "Haben Sie Fragen? Rufen Sie uns an.",
    ]
    return lines, sender, {"Versichertennummer": kvnr}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], [
        AmountLabel(str(principal), "to_pay"),
        AmountLabel(str(fee), "to_pay"),
        AmountLabel(str(total), "to_pay"),
    ]


def insurance_questionnaire(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(INSURERS)
    kvnr = f"{r.pick(['B', 'E', 'S'])}{r.digits(9)}"
    due = working_after(ctx.letter_date, r.pick([21, 28]))
    lines = _header(ctx, [sender, "Mitgliederservice"], [f"Versichertennummer {kvnr}"])
    lines += [
        "Fragebogen zur Familienversicherung",
        "",
        "wir prüfen regelmäßig, ob die Voraussetzungen der Familienversicherung",
        "noch vorliegen. Bitte füllen Sie den beigefügten Fragebogen aus und",
        f"senden Sie ihn bis zum {ctx.d(due)} zurück.",
        "Ohne Ihre Angaben können wir die Familienversicherung nicht fortführen.",
    ]
    return lines, sender, {"Versichertennummer": kvnr}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], []



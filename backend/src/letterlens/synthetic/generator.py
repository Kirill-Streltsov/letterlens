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


def insurance_rejection(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(INSURERS)
    kvnr = f"{r.pick(['C', 'H', 'R'])}{r.digits(9)}"
    rel = r.pick(RELATIVE_OBJECTION)
    item = r.pick(["eine Haushaltshilfe", "eine Reha-Maßnahme", "einen Rollstuhl", "Fahrkosten"])
    lines = _header(ctx, [sender, "Leistungsabteilung"], [f"Versichertennummer: {kvnr}"])
    lines += [
        "Bescheid über Ihren Antrag",
        "",
        f"Ihren Antrag auf Kostenübernahme für {item} müssen wir leider ablehnen.",
        "Nach Prüfung durch den Medizinischen Dienst liegen die Voraussetzungen nicht vor.",
        "",
        "Rechtsbehelfsbelehrung",
        f"Gegen diesen Bescheid können Sie {rel} Widerspruch einlegen.",
    ]
    return lines, sender, {"Versichertennummer": kvnr}, [
        DeadlineLabel("relative", relative_expression=rel)
    ], []


# --------------------------------------------------------------------------
# Templates: IMMIGRATION
# --------------------------------------------------------------------------


def immigration_appointment(ctx: Ctx) -> Built:
    r = ctx.rnd
    city = r.pick(["Bochum", "Dortmund", "Essen", "Duisburg"])
    sender = f"Stadt {city} - Ausländerbehörde"
    az = f"{r.digits(2)}.{r.digits(2)}-{r.digits(5)}"
    appt = working_after(ctx.letter_date, r.pick([9, 15, 20]))
    time = r.pick(["08:00", "09:40", "10:20", "14:00"])
    expiry = ctx.letter_date + timedelta(days=r.r.randint(20, 60))
    fee = r.pick([Decimal("93.00"), Decimal("98.00"), Decimal("100.00")])
    lines = _header(ctx, [sender, "Bürgerservice Migration"], [f"Aktenzeichen: {az}"])
    lines += [
        "Terminbestätigung zur Verlängerung Ihrer Aufenthaltserlaubnis",
        "",
        f"Ihre Aufenthaltserlaubnis ist gültig bis {ctx.d(expiry)}.",
        f"Ihr Termin: {ctx.d(appt)}, {time} Uhr.",
        "Bitte bringen Sie mit: Reisepass, biometrisches Foto, Nachweis über Einkommen,",
        "Mietvertrag und Nachweis der Krankenversicherung.",
        f"Die Gebühr beträgt voraussichtlich {ctx.m(fee)}.",
        "Bitte sagen Sie den Termin ab, wenn Sie ihn nicht wahrnehmen können.",
    ]
    return lines, sender, {"Aktenzeichen": az}, [
        DeadlineLabel("appointment", date=appt.isoformat())
    ], [AmountLabel(str(fee), "to_pay")]


def immigration_hearing(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(["Kreis Recklinghausen - Ausländeramt", "Stadt Herne - Ausländerbehörde"])
    az = f"AB-{r.digits(4)}/{ctx.letter_date.year}"
    due = working_after(ctx.letter_date, r.pick([14, 21]))
    lines = _header(ctx, [sender, "Fachbereich Ordnung"], [f"Az.: {az}"])
    lines += [
        "Anhörung nach § 28 Verwaltungsverfahrensgesetz",
        "",
        "wir beabsichtigen, Ihren Antrag auf Erteilung einer Niederlassungserlaubnis",
        "abzulehnen, weil der Nachweis ausreichender Deutschkenntnisse fehlt.",
        f"Sie haben Gelegenheit, sich bis zum {ctx.d(due)} schriftlich zu äußern.",
        "Sie können auch fehlende Nachweise einreichen.",
        "Nach Ablauf der Frist entscheiden wir nach Aktenlage.",
    ]
    return lines, sender, {"Aktenzeichen": az}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], []


def immigration_fiction(ctx: Ctx) -> Built:
    r = ctx.rnd
    city = r.pick(["Gelsenkirchen", "Mülheim an der Ruhr", "Bochum"])
    sender = f"Ausländerbehörde {city}"
    az = f"{r.digits(3)}-{r.digits(6)}"
    due = working_after(ctx.letter_date, r.pick([14, 28]))
    lines = _header(ctx, [sender, "Abteilung Aufenthalt"], [f"Aktenzeichen {az}"])
    lines += [
        "Ihr Antrag auf Verlängerung des Aufenthaltstitels",
        "",
        "Ihr Antrag ist bei uns eingegangen. Bis zur Entscheidung gilt Ihr bisheriger",
        "Aufenthaltstitel als fortbestehend (Fiktionsbescheinigung nach § 81 Abs. 4 AufenthG).",
        f"Für die Bearbeitung fehlen noch Unterlagen. Bitte reichen Sie diese bis {ctx.d(due)} ein:",
        "- Arbeitsvertrag und letzte drei Gehaltsabrechnungen",
        "- Nachweis über ausreichenden Wohnraum",
    ]
    return lines, sender, {"Aktenzeichen": az}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], []


# --------------------------------------------------------------------------
# Templates: LANDLORD
# --------------------------------------------------------------------------

LANDLORDS = [
    "Wohnbau Ruhr GmbH", "Revier Wohnen eG", "Hausverwaltung Schmitz & Partner",
    "Emscher Immobilien GmbH", "Stadtteil Wohnungsgenossenschaft eG",
]  # fmt: skip


def landlord_utility_statement(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(LANDLORDS)
    unit = f"{r.digits(4)}-{r.digits(3)}"
    year = ctx.letter_date.year - 1
    balance = r.amount(40, 980)
    refund = r.r.random() < 0.3
    advance = r.amount(120, 340)
    start = (ctx.letter_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    lines = _header(ctx, [sender, "Abteilung Betriebskosten"], [f"Mietobjekt-Nr.: {unit}"])
    lines += [
        f"Betriebskostenabrechnung für den Zeitraum 01.01.{year} bis 31.12.{year}",
        "",
        "anbei erhalten Sie die Abrechnung der Betriebskosten.",
    ]
    deadlines: list[DeadlineLabel] = []
    if refund:
        lines.append(f"Es ergibt sich ein Guthaben von {ctx.m(balance)}.")
        lines.append("Das Guthaben wird mit der nächsten Miete verrechnet.")
        amounts = [AmountLabel(str(balance), "to_receive")]
    else:
        rel = r.pick(["innerhalb von 30 Tagen nach Erhalt", "binnen 30 Tagen nach Erhalt"])
        lines.append(f"Es ergibt sich eine Nachzahlung von {ctx.m(balance)}.")
        lines.append(f"Bitte überweisen Sie den Betrag {rel} dieser Abrechnung.")
        amounts = [AmountLabel(str(balance), "to_pay")]
        deadlines.append(DeadlineLabel("relative", relative_expression=rel))
    lines += [
        f"Ab dem {ctx.d(start)} beträgt Ihre monatliche Vorauszahlung {ctx.m(advance)}.",
        "Belege können Sie nach Terminvereinbarung bei uns einsehen.",
    ]
    amounts.append(AmountLabel(str(advance), "info"))
    return lines, sender, {"Mietobjekt-Nr.": unit}, deadlines, amounts


def landlord_rent_increase(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(LANDLORDS)
    unit = f"{r.digits(4)}-{r.digits(3)}"
    old = r.amount(380, 820)
    new = old + Decimal(r.r.randint(20, 90))
    # Consent period: until the end of the second calendar month after receipt.
    third_month = ctx.letter_date.replace(day=1) + timedelta(days=95)
    consent = third_month.replace(day=1) - timedelta(days=1)
    effective = consent + timedelta(days=1)
    lines = _header(ctx, [sender, "Vermietung"], [f"Mieternummer: {unit}"])
    lines += [
        "Mieterhöhungsverlangen nach § 558 BGB",
        "",
        f"Ihre derzeitige Nettokaltmiete beträgt {ctx.m(old)}.",
        "Unter Bezug auf den Mietspiegel bitten wir um Zustimmung zur Erhöhung",
        f"auf {ctx.m(new)} ab dem {ctx.d(effective)}.",
        f"Bitte erteilen Sie Ihre Zustimmung bis zum {ctx.d(consent)}.",
        "Den Mietspiegel und die Berechnung finden Sie in der Anlage.",
    ]
    return lines, sender, {"Mieternummer": unit}, [
        DeadlineLabel("explicit_date", date=consent.isoformat())
    ], [AmountLabel(str(old), "info"), AmountLabel(str(new), "to_pay")]


def landlord_reminder(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(LANDLORDS)
    unit = f"{r.digits(4)}-{r.digits(3)}"
    arrears = r.amount(300, 1800)
    due = working_after(ctx.letter_date, r.pick([7, 10]))
    lines = _header(ctx, [sender, "Mietenbuchhaltung"], [f"Vertragsnummer {unit}"])
    lines += [
        r.pick(["Mahnung - Mietrückstand", "Zahlungserinnerung Miete"]),
        "",
        f"auf Ihrem Mietkonto besteht ein Rückstand von {ctx.m(arrears)}.",
        f"Bitte gleichen Sie den Rückstand bis spätestens {ctx.d(due)} aus.",
        "Bei weiterem Zahlungsverzug behalten wir uns rechtliche Schritte vor.",
        "Wenn Sie Schwierigkeiten haben, sprechen Sie uns bitte an.",
    ]
    return lines, sender, {"Vertragsnummer": unit}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], [AmountLabel(str(arrears), "to_pay")]


# --------------------------------------------------------------------------
# Templates: OTHER
# --------------------------------------------------------------------------


def broadcast_fee(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = "ARD ZDF Deutschlandradio Beitragsservice"
    nr = f"{r.digits(3)} {r.digits(3)} {r.digits(3)}"
    amount = r.pick([Decimal("55.08"), Decimal("110.16"), Decimal("165.24")])
    due = working_after(ctx.letter_date, 14)
    lines = _header(ctx, [sender, "50656 Köln"], [f"Beitragsnummer: {nr}"])
    lines += [
        "Zahlungsaufforderung",
        "",
        f"für Ihre Wohnung sind Rundfunkbeiträge in Höhe von {ctx.m(amount)} offen.",
        f"Bitte überweisen Sie den Betrag bis zum {ctx.d(due)}.",
        "Unter bestimmten Voraussetzungen ist eine Befreiung möglich.",
    ]
    return lines, sender, {"Beitragsnummer": nr}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], [AmountLabel(str(amount), "to_pay")]


def collection_agency(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(["Inkasso Westfalen GmbH", "Rhein-Ruhr Forderungsmanagement GmbH"])
    case = f"IK-{r.digits(7)}"
    claim = r.amount(40, 600)
    costs = r.amount(15, 90)
    total = claim + costs
    due = working_after(ctx.letter_date, r.pick([7, 10, 14]))
    lines = _header(ctx, [sender, "Forderungsabteilung"], [f"Unser Zeichen: {case}"])
    lines += [
        "Zahlungsaufforderung im Auftrag unserer Mandantin",
        "",
        f"Hauptforderung: {ctx.m(claim)}",
        f"Inkassokosten: {ctx.m(costs)}",
        f"Gesamtforderung: {ctx.m(total)}",
        f"Zahlen Sie den Gesamtbetrag bis zum {ctx.d(due)}.",
        "Prüfen Sie die Forderung. Bei Fragen wenden Sie sich an uns.",
    ]
    return lines, sender, {"Unser Zeichen": case}, [
        DeadlineLabel("explicit_date", date=due.isoformat())
    ], [
        AmountLabel(str(claim), "to_pay"),
        AmountLabel(str(costs), "to_pay"),
        AmountLabel(str(total), "to_pay"),
    ]


def utility_installment(ctx: Ctx) -> Built:
    r = ctx.rnd
    sender = r.pick(["Stadtwerke Bochum", "DEW21 Dortmund", "Stadtwerke Essen"])
    customer = r.digits(9)
    new = r.amount(45, 160)
    start = (ctx.letter_date.replace(day=1) + timedelta(days=32)).replace(day=1)
    lines = _header(ctx, [sender, "Kundenservice"], [f"Kundennummer: {customer}"])
    lines += [
        "Anpassung Ihres monatlichen Abschlags",
        "",
        f"ab dem {ctx.d(start)} beträgt Ihr Abschlag für Strom {ctx.m(new)}.",
        "Der Betrag wird wie gewohnt per Lastschrift eingezogen.",
        "Sie müssen nichts weiter tun.",
    ]
    return lines, sender, {"Kundennummer": customer}, [], [AmountLabel(str(new), "info")]


# --------------------------------------------------------------------------
# Registry and noise
# --------------------------------------------------------------------------

Template = Callable[[Ctx], Built]

TEMPLATES: dict[LetterType, dict[str, Template]] = {
    LetterType.TAX: {
        "tax_assessment": tax_assessment,
        "tax_reminder": tax_reminder,
        "tax_arrears": tax_arrears,
    },
    LetterType.BENEFITS: {
        "jobcenter_approval": jobcenter_approval,
        "jobcenter_documents": jobcenter_documents,
        "jobcenter_invitation": jobcenter_invitation,
        "familienkasse_refund": familienkasse_refund,
    },

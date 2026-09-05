"""Hand-written letters with layouts that no template uses.

They test generalization beyond the synthetic templates. Names and numbers
are invented. Labels follow the same format as synthetic letters.
"""

from __future__ import annotations

from letterlens.synthetic.generator import AmountLabel, DeadlineLabel, SyntheticLetter


def _l(
    id_: str,
    type_: str,
    sender: str,
    letter_date: str,
    lines: str,
    deadlines: list[DeadlineLabel],
    amounts: list[AmountLabel],
) -> SyntheticLetter:
    return SyntheticLetter(
        id=f"hw-{id_}",
        letter_type=type_,
        template_id=f"handwritten-{id_}",
        lines=[x.strip() for x in lines.strip().splitlines()],
        sender=sender,
        letter_date=letter_date,
        references={},
        deadlines=deadlines,
        amounts=amounts,
    )


HANDWRITTEN: list[SyntheticLetter] = [
    _l(
        "court-order",
        "other",
        "Amtsgericht Hagen",
        "2026-10-12",
        """
        Amtsgericht Hagen - Zentrales Mahngericht -
        58084 Hagen
        Geschäftszeichen: 26-4471123-0-3
        Hagen, 12.10.2026
        Mahnbescheid
        Antragsteller: Fernabsatz Direkt GmbH
        Hauptforderung: 389,90 EUR
        Kosten des Verfahrens: 36,00 EUR
        Gesamtbetrag: 425,90 EUR
        Sie können gegen den Anspruch Widerspruch erheben, und zwar innerhalb von zwei Wochen ab Zustellung.
        Verwenden Sie dafür den beigefügten Vordruck.
    """,
        [DeadlineLabel("relative", relative_expression="innerhalb von zwei Wochen ab Zustellung")],
        [AmountLabel("389.90", "to_pay"), AmountLabel("36.00", "to_pay"), AmountLabel("425.90", "to_pay")],
    ),
    _l(
        "fine",
        "other",
        "Kreis Unna - Bußgeldstelle",
        "2026-09-03",
        """
        Kreis Unna - Der Landrat - Bußgeldstelle
        Friedrich-Ebert-Straße 17, 59425 Unna
        Aktenzeichen 701.334512.3
        Unna, den 03.09.2026
        Bußgeldbescheid
        Ihnen wird vorgeworfen, am 14.08.2026 die zulässige Höchstgeschwindigkeit überschritten zu haben.
        Geldbuße: 70,00 €   Gebühr: 25,00 €   Auslagen: 3,50 €
        Gesamtbetrag 98,50 €
        Der Bescheid wird rechtskräftig, wenn kein Einspruch innerhalb von zwei Wochen nach Zustellung eingelegt wird.
        Zahlen Sie den Gesamtbetrag bitte bis zum 01.10.2026.
    """,
        [
            DeadlineLabel("relative", relative_expression="innerhalb von zwei Wochen nach Zustellung"),
            DeadlineLabel("explicit_date", date="2026-10-01"),
        ],
        [
            AmountLabel("70.00", "to_pay"),
            AmountLabel("25.00", "to_pay"),
            AmountLabel("3.50", "to_pay"),
            AmountLabel("98.50", "to_pay"),
        ],
    ),
    _l(
        "termination",
        "landlord",
        "Hausverwaltung Kerkhoff",
        "2026-06-30",
        """
        Hausverwaltung Kerkhoff
        Wittener Straße 220 · 44803 Bochum
        Bochum, 30. Juni 2026
        Kündigung des Mietverhältnisses über die Wohnung Hustadtring 41, 2. OG links
        hiermit kündigen wir das Mietverhältnis fristgemäß zum 31.12.2026 wegen Eigenbedarfs.
        Wir bitten Sie, die Wohnung bis zum 31.12.2026 geräumt zu übergeben.
        Auf Ihr Widerspruchsrecht nach § 574 BGB weisen wir hin. Der Widerspruch muss spätestens zwei Monate vor Beendigung erklärt werden.
    """,
        [DeadlineLabel("explicit_date", date="2026-12-31")],
        [],
    ),
    _l(
        "jobcenter-change",
        "benefits",
        "Jobcenter EN",
        "2026-08-17",
        """
        Jobcenter EN
        Standort Witten
        Datum: 17.08.2026
        Änderungsbescheid
        Wegen der Aufnahme Ihrer Beschäftigung werden die Leistungen ab 01.09.2026 neu berechnet.
        Neuer monatlicher Anspruch: 312,44 EUR
        Für August wurden 214,10 EUR zu viel gezahlt. Dieser Betrag ist zu erstatten.
        Bitte überweisen Sie 214,10 EUR bis 30.09.2026.
        Gegen diesen Bescheid kann innerhalb eines Monats nach Bekanntgabe Widerspruch erhoben werden.
    """,
        [
            DeadlineLabel("explicit_date", date="2026-09-30"),
            DeadlineLabel("relative", relative_expression="innerhalb eines Monats nach Bekanntgabe"),
        ],
        [AmountLabel("312.44", "to_receive"), AmountLabel("214.10", "to_pay")],
    ),
    _l(
        "kindergeld-school",
        "benefits",
        "Familienkasse Nordrhein-Westfalen Ost",
        "2026-09-21",
        """

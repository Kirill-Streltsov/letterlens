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
        Familienkasse Nordrhein-Westfalen Ost
        Kindergeldnummer 615FK112233
        Datum 21.09.2026
        Überprüfung des Kindergeldanspruchs
        Bitte legen Sie bis zum 23.10.2026 eine Schulbescheinigung für Ihr Kind vor.
        Ohne Nachweis müssen wir die Zahlung einstellen.
    """,
        [DeadlineLabel("explicit_date", date="2026-10-23")],
        [],
    ),
    _l(
        "sick-pay",
        "health_insurance",
        "BKK Ruhr",
        "2026-05-11",
        """
        BKK Ruhr · Krankengeld
        Versicherten-Nr. Q554433221
        Datum: 11.05.2026
        Bescheid über Krankengeld
        Ab dem 04.05.2026 zahlen wir Ihnen Krankengeld in Höhe von 61,17 EUR kalendertäglich.
        Bitte senden Sie uns den Auszahlschein spätestens am 25.05.2026 zurück.
        Gegen diesen Bescheid ist der Widerspruch innerhalb eines Monats nach Bekanntgabe zulässig.
    """,
        [
            DeadlineLabel("explicit_date", date="2026-05-25"),
            DeadlineLabel("relative", relative_expression="innerhalb eines Monats nach Bekanntgabe"),
        ],
        [AmountLabel("61.17", "to_receive")],
    ),
    _l(
        "care-insurance",
        "health_insurance",
        "AOK Rheinland/Hamburg - Pflegekasse",
        "2026-03-02",
        """
        AOK Rheinland/Hamburg - Die Pflegekasse
        Datum: 02.03.2026
        Begutachtung zur Feststellung der Pflegebedürftigkeit
        Der Medizinische Dienst besucht Sie am 17.03.2026 zwischen 9 und 12 Uhr.
        Halten Sie bitte Arztberichte und den Medikamentenplan bereit.
    """,
        [DeadlineLabel("explicit_date", date="2026-03-17")],
        [],
    ),
    _l(
        "exit-request",
        "immigration",
        "Stadt Hagen - Ausländerbehörde",
        "2026-04-08",
        """
        Stadt Hagen

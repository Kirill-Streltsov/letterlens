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

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



from datetime import date
from decimal import Decimal

from letterlens.domain import (
    ExtractedAmount,
    ExtractedDate,
    ExtractedDeadline,
    ExtractedReference,
    ExtractedText,
    Extraction,
    FactStatus,
    LetterDocument,
    OcrLine,
)
from letterlens.grounding.verifier import NOTE_NO_DATE, NOTE_NOT_IN_SOURCE, NOTE_OTHER_LINE, verify

LINES = [
    "Finanzamt Bochum-Mitte",
    "Steuernummer: 123/456/78901",
    "Datum: 10.03.2026",
    "Nachzahlung: 1.523,00 €",
    "Bitte zahlen Sie den Betrag bis zum 14.04.2026.",
    "Der Einspruch ist innerhalb eines Monats nach Bekanntgabe einzulegen.",
]
DOC = LetterDocument(lines=[OcrLine(page=1, index=i, text=t) for i, t in enumerate(LINES, 1)])


def extraction(**overrides: object) -> Extraction:
    base: dict[str, object] = {
        "sender": ExtractedText(value="Finanzamt Bochum-Mitte", line_ids=["p1-l1"]),
        "subject": ExtractedText(value=None, line_ids=[]),
        "letter_date": ExtractedDate(value="2026-03-10", line_ids=["p1-l3"]),
        "reference_numbers": [
            ExtractedReference(label="Steuernummer", value="123/456/78901", line_ids=["p1-l2"])
        ],
        "deadlines": [
            ExtractedDeadline(
                kind="explicit_date",
                date="2026-04-14",
                relative_expression=None,
                description="Pay",
                line_ids=["p1-l5"],
            ),
            ExtractedDeadline(
                kind="relative",
                date=None,
                relative_expression="innerhalb eines Monats nach Bekanntgabe",
                description="Objection",
                line_ids=["p1-l6"],
            ),
        ],
        "amounts": [
            ExtractedAmount(
                value="1523.00", currency="EUR", description="Due", direction="to_pay", line_ids=["p1-l4"]
            )
        ],
        "required_actions": [],
    }
    base.update(overrides)
    return Extraction(**base)  # type: ignore[arg-type]


def test_grounded_facts_are_verified() -> None:
    facts = verify(extraction(), DOC)
    assert facts.letter_date == date(2026, 3, 10)
    assert facts.letter_date_status is FactStatus.VERIFIED
    pay, objection = facts.deadlines
    assert pay.status is FactStatus.VERIFIED and pay.due_date == date(2026, 4, 14)
    assert objection.is_estimate and objection.status is FactStatus.NEEDS_CHECK
    assert objection.due_date == date(2026, 4, 16)
    assert facts.amounts[0].value == Decimal("1523.00")
    assert facts.amounts[0].status is FactStatus.VERIFIED
    assert facts.grounding_rate == 1.0


def test_hallucinated_date_needs_check() -> None:
    wrong = ExtractedDeadline(
        kind="explicit_date",
        date="2026-04-20",
        relative_expression=None,
        description="Pay",
        line_ids=["p1-l5"],
    )
    facts = verify(extraction(deadlines=[wrong]), DOC)
    # A date that is nowhere in the letter is not shown at all, not even as "please check".
    assert facts.deadlines[0].status is FactStatus.NEEDS_CHECK
    assert facts.deadlines[0].due_date is None
    assert facts.deadlines[0].note == NOTE_NO_DATE
    assert facts.grounding_rate < 1.0


def test_wrong_line_citation_needs_check() -> None:
    misplaced = ExtractedAmount(
        value="1523.00", currency="EUR", description="Due", direction="to_pay", line_ids=["p1-l1"]
    )
    facts = verify(extraction(amounts=[misplaced]), DOC)
    assert facts.amounts[0].status is FactStatus.NEEDS_CHECK
    assert facts.amounts[0].note == NOTE_OTHER_LINE


def test_unknown_line_ids_are_dropped() -> None:
    bad = ExtractedAmount(
        value="1523.00", currency="EUR", description="Due", direction="to_pay", line_ids=["p9-l99"]
    )
    facts = verify(extraction(amounts=[bad]), DOC)
    assert facts.amounts[0].line_ids == []
    assert facts.amounts[0].status is FactStatus.NEEDS_CHECK


def test_relative_deadline_must_be_in_cited_line() -> None:
    invented = ExtractedDeadline(
        kind="relative",
        date=None,
        relative_expression="innerhalb von zwei Wochen",
        description="Reply",
        line_ids=["p1-l4"],
    )
    facts = verify(extraction(deadlines=[invented]), DOC)
    assert facts.deadlines[0].due_date is None
    assert facts.deadlines[0].note == NOTE_NOT_IN_SOURCE


def test_reference_not_in_letter_is_dropped() -> None:
    fake_ref = ExtractedReference(label="Aktenzeichen", value="XYZ-1", line_ids=["p1-l2"])
    facts = verify(extraction(reference_numbers=[fake_ref]), DOC)
    assert facts.reference_numbers == []


def test_letter_date_hint_is_a_whole_word() -> None:
    # Regression: "den " inside "Studierenden" made a permission date look like the letter date.
    lines = ["Stadt Bochum", "Seit dem 01.03.2024 ist es ausländischen Studierenden erlaubt, zu arbeiten."]
    doc = LetterDocument(lines=[OcrLine(page=1, index=i, text=t) for i, t in enumerate(lines, 1)])
    empty = extraction(letter_date=ExtractedDate(value=None, line_ids=[]), deadlines=[], amounts=[])
    assert verify(empty, doc).letter_date is None


# --- Findings from real and sample letters (see docs/ai/evaluation.md, "Real letters") ---------

REAL = LetterDocument(
    lines=[
        OcrLine(page=1, index=i, text=t)
        for i, t in enumerate(
            [
                "Stadt Musterstadt - Bußgeldstelle",
                "Datum 08.02.2018",
                "Geldbuße  380, 00  EUR",
                "Festgesetzt werden  52.112,00  2.146,32",
                "über einen Gesamtbetrag in Höhe von  _EUR",
                "Bitte reichen Sie bis zum TT.MM.2015 den Mietvertrag ein.",
                "wenn Sie nicht innerhalb von zwei Wochen nach seiner Zustellung Einspruch einlegen.",
            ],
            1,
        )
    ]
)


def _amount(value: str, line: str) -> ExtractedAmount:
    return ExtractedAmount(value=value, currency="EUR", description="x", direction="to_pay", line_ids=[line])


def _deadline(day: str, line: str) -> ExtractedDeadline:
    return ExtractedDeadline(
        kind="explicit_date", date=day, relative_expression=None, description="x", line_ids=[line]
    )


def test_ocr_space_after_decimal_comma_and_table_amounts_are_verified() -> None:
    facts = verify(
        extraction(deadlines=[], amounts=[_amount("380.00", "p1-l3"), _amount("52112.00", "p1-l4")]), REAL
    )
    assert [a.status for a in facts.amounts] == [FactStatus.VERIFIED, FactStatus.VERIFIED]


def test_amount_from_a_blank_field_is_dropped() -> None:
    facts = verify(
        extraction(deadlines=[], amounts=[_amount("0.00", "p1-l5"), _amount("0.01", "p1-l5")]), REAL
    )
    assert facts.amounts == []


def test_placeholder_date_is_not_shown() -> None:
    facts = verify(
        extraction(
            amounts=[],
            deadlines=[_deadline("2015-11-01", "p1-l6")],
            letter_date=ExtractedDate(value="2015-11-01", line_ids=["p1-l6"]),
        ),
        REAL,
    )
    assert facts.deadlines[0].due_date is None
    assert facts.deadlines[0].note == NOTE_NO_DATE
    assert facts.letter_date == date(2018, 2, 8)  # the header date, not the invented one


def test_computed_date_is_replaced_by_the_documented_estimate() -> None:
    # The model added two weeks itself; the verifier recomputes it with the rule and says how.
    facts = verify(extraction(amounts=[], deadlines=[_deadline("2018-02-22", "p1-l7")]), REAL)
    d = facts.deadlines[0]
    assert d.is_estimate and d.rule and d.due_date is not None
    assert "envelope" in (d.note or "")  # formal delivery: the date on the envelope counts


def test_assessed_and_withheld_amounts_are_not_to_pay() -> None:
    doc = LetterDocument(
        lines=[
            OcrLine(page=1, index=i, text=x)
            for i, x in enumerate(
                [
                    "Finanzamt Lindenhagen",
                    "Datum: 15.06.2026",
                    "restgesetzt weraen..  6.418,00",
                    "ab Steuerabzug vom Lohn  5.977,00",
                    "demnach zu wenig gezahlt  441,00",
                ],
                1,
            )
        ]
    )
    amounts = [_amount("6418.00", "p1-l3"), _amount("5977.00", "p1-l4"), _amount("441.00", "p1-l5")]
    facts = verify(
        extraction(
            deadlines=[], amounts=amounts, letter_date=ExtractedDate(value="2026-06-15", line_ids=["p1-l2"])
        ),
        doc,
    )
    assert [a.direction for a in facts.amounts] == ["info", "info", "to_pay"]

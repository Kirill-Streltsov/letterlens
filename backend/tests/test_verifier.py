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
from letterlens.grounding.verifier import NOTE_NOT_IN_SOURCE, NOTE_OTHER_LINE, verify

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

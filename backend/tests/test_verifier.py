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



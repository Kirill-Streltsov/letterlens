from letterlens.domain import LetterDocument, OcrLine
from letterlens.extraction.rules import extract_with_rules


def doc(*lines: str) -> LetterDocument:
    return LetterDocument(lines=[OcrLine(page=1, index=i, text=t) for i, t in enumerate(lines, 1)])


def test_letter_date_from_the_header() -> None:
    extraction = extract_with_rules(doc("Stadt Kleinhausen", "Kleinhausen, den 03.11.2026", "Ihr Antrag"))
    assert extraction.letter_date.value == "2026-11-03"


def test_receipt_form_date_is_not_the_letter_date() -> None:
    extraction = extract_with_rules(
        doc(
            "Stadt Kleinhausen - Ausländerbehörde",
            "Gegen Empfangsbekenntnis",
            "Ihre Aufenthaltserlaubnis wurde verlängert.",
            "Empfangsbekenntnis",
            "Das vorstehende Schriftstück habe ich heute erhalten und zur Kenntnis genommen.",
            "Kleinhausen, den 04.05.2026",
        )
    )
    assert extraction.letter_date.value is None

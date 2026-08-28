from letterlens.domain import LetterDocument, OcrLine
from letterlens.safety.pii import PiiVault, scrub_for_logs
from letterlens.synthetic import generate_corpus, to_document


def doc(*lines: str) -> LetterDocument:
    return LetterDocument(lines=[OcrLine(page=1, index=i, text=t) for i, t in enumerate(lines, 1)])


def test_identifiers_are_pseudonymized_and_restored() -> None:
    vault = PiiVault()
    text = (
        "IBAN DE89 3704 0044 0532 0130 00, Steuernummer 123/456/78901, "
        "Identifikationsnummer: 12 345 678 901, mail ayse@example.org, Tel. 0234 1234567"
    )
    redacted = vault.redact_text(text)
    for secret in ("DE89", "123/456/78901", "12 345 678 901", "ayse@example.org", "1234567"):
        assert secret not in redacted
    assert vault.restore(redacted) == text


def test_dates_and_amounts_survive() -> None:
    vault = PiiVault()
    text = "Bitte zahlen Sie 1.523,00 € bis zum 05.01.2027, Postfach 1234, 44787 Bochum"
    assert vault.redact_text(text) == text


def test_address_block_name_and_street() -> None:
    vault = PiiVault()
    redacted = vault.redact_document(
        doc(
            "Finanzamt Bochum-Mitte",
            "Postfach 1234",
            "44701 Bochum",
            "Ayşe Yılmaz",
            "Bergstraße 49",
            "45127 Essen",
            "Datum: 10.01.2026",
        )
    )
    texts = [line.text for line in redacted.lines]
    assert texts[0] == "Finanzamt Bochum-Mitte"  # sender is kept
    assert texts[3] == "[NAME_1]"
    assert texts[4] == "[ADDRESS_1]"
    assert vault.restore("Dear [NAME_1]") == "Dear Ayşe Yılmaz"


def test_same_value_same_placeholder() -> None:
    vault = PiiVault()
    a = vault.redact_text("BG-Nummer 12345BG0012345")
    b = vault.redact_text("Ihre 12345BG0012345")
    assert a.split()[-1] == b.split()[-1]


def test_synthetic_letters_have_no_recipient_names_after_redaction() -> None:
    for letter in generate_corpus(2):
        vault = PiiVault()
        redacted = vault.redact_document(to_document(letter)).plain_text()
        name = next(line for line in letter.lines[3:8] if line and " " in line and not line[0].isdigit())
        assert name not in redacted, letter.id


def test_restore_nested() -> None:
    vault = PiiVault()
    vault.redact_text("x@y.de")
    assert vault.restore({"a": ["[EMAIL_1]"], "b": 1}) == {"a": ["x@y.de"], "b": 1}


def test_scrub_for_logs() -> None:
    assert "4711" not in scrub_for_logs("Kundennummer: 4711-0815 Frau Müller")

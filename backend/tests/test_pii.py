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


def test_name_with_ocr_noise_and_greeting_is_hidden_everywhere() -> None:
    # Regression from a real letter: OCR appended "c 030" to the name line, and the
    # name appeared again in the greeting. Both must be replaced.
    vault = PiiVault()
    redacted = vault.redact_document(
        doc(
            "Stadt Dortmund 38/2-2 44122 Dortmund",
            "Max Mustermann c 030",
            "Saarbrücker Straße 21",
            "44135 Dortmund Herr Beispiel",
            "Guten Tag Max Mustermann, |",
            "Sie haben die Verlängerung beantragt. Herr Mustermann, bitte beachten Sie:",
        )
    ).plain_text()
    assert "Mustermann" not in redacted
    assert "Saarbrücker" not in redacted
    assert "Stadt Dortmund" in redacted  # the sender stays
    assert vault.restore("[NAME_1]") == "Max Mustermann"


def test_greeting_without_address_block() -> None:
    vault = PiiVault()
    redacted = vault.redact_document(
        doc("Sehr geehrter Herr Demir,", "Ihr Antrag, Herr Demir, ist eingegangen.")
    ).plain_text()
    assert "Demir" not in redacted


def test_generic_greeting_is_not_a_name() -> None:
    vault = PiiVault()
    redacted = vault.redact_document(
        doc("Sehr geehrte Damen und Herren,", "Mit freundlichen Grüßen")
    ).plain_text()
    assert redacted == "Sehr geehrte Damen und Herren,\nMit freundlichen Grüßen"


def test_reapply_hides_restored_names_and_addresses_again() -> None:
    lines = [
        "Max Mustermann",
        "Lindenallee 7",
        "44787 Bochum",
        "Guten Tag Max Mustermann,",
        "Ihre IBAN DE89370400440532013000",
    ]
    doc = LetterDocument(lines=[OcrLine(page=1, index=i + 1, text=t) for i, t in enumerate(lines)])
    vault = PiiVault()
    vault.redact_document(doc)
    text = "Mr Mustermann (Max Mustermann, Lindenallee 7) must pay from DE89370400440532013000."
    hidden = vault.reapply(text)
    assert "Mustermann" not in hidden and "Lindenallee" not in hidden and "DE8937" not in hidden
    # The surname alone shares the full name's placeholder (as in redact_document).
    assert vault.restore(hidden) == text.replace("Mr Mustermann", "Mr Max Mustermann")

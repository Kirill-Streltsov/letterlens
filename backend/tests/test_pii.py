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



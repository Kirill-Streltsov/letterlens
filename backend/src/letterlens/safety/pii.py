"""Reversible pseudonymization of personal data before text reaches a model.

The model sees placeholders such as ``[IBAN_1]``. After the model call the
vault puts the original values back. The vault lives only in memory for the
duration of one pipeline step and is never stored or logged.

Limitations (documented in docs/security/data-protection.md): person names
are detected only in the address block, by heuristics.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from letterlens.domain import LetterDocument, OcrLine


@dataclass(frozen=True, slots=True)
class Rule:
    kind: str
    pattern: re.Pattern[str]
    group: int = 0


# Order matters: specific identifiers first, generic ones last.
RULES: list[Rule] = [
    Rule("IBAN", re.compile(r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,7}(?:\s?[A-Z0-9]{1,3})?\b")),
    Rule("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    Rule(
        "TAXID",
        re.compile(
            r"(?i)(?:identifikationsnummer|steuer-?id|idnr\.?)\s*:?\s*(\d{2}\s?\d{3}\s?\d{3}\s?\d{3})"
        ),
        1,
    ),
    Rule("TAXNO", re.compile(r"\b\d{2,3}/\d{3,4}/\d{4,5}\b")),
    Rule("BGNO", re.compile(r"\b\d{5}BG\d{7}\b")),
    Rule("INSURANCENO", re.compile(r"\b[A-Z]\d{9}\b")),
    Rule(
        "BIRTHDATE",
        re.compile(r"(?i)(?:geb\.(?:\s*am)?|geboren\s+am|geburtsdatum:?)\s*(\d{1,2}\.\d{1,2}\.\d{2,4})"),
        1,
    ),
    Rule("PHONE", re.compile(r"(?<![\d.,/])(?:\+49|0049|0)\s?\d{2,5}[\s/-]?\d{3,}(?:[\s-]?\d{2,})*\b")),
    Rule(
        "REFNO",
        re.compile(
            r"(?i)(?:kundennummer|kunden-nr\.?|aktenzeichen|az\.|vertragsnummer|mieternummer|"
            r"beitragsnummer|unser zeichen|kindergeld-nr\.|mietobjekt-nr\.)\s*:?\s*"
            r"([A-Z0-9][\w./-]{2,}(?:\s\d[\w./-]*)*)"
        ),
        1,
    ),
]

_POSTCODE_CITY = re.compile(r"^\d{5}\s+[A-ZÄÖÜ][\wäöüß. -]+$")
_STREET = re.compile(r"^[A-ZÄÖÜ][\wäöüß. -]+\s\d{1,4}\s?[a-zA-Z]?$")
_PERSON = re.compile(r"^(?:[A-ZÄÖÜÇŞİ][\w'-]+)(?:\s+[A-ZÄÖÜÇŞİ][\w'-]+){1,3}$")
_ORG_WORDS = re.compile(
    r"(?i)finanzamt|jobcenter|stadt|kreis|gmbh|\beg\b|kasse|behörde|amt\b|service|"
    r"versicherung|aok|barmer|dak|ikk|stadtwerke|inkasso|hausverwaltung|postfach|abteilung"
)


@dataclass
class PiiVault:
    """Holds placeholder-to-value mappings for one request."""

    _forward: dict[str, str] = field(default_factory=dict)
    _reverse: dict[str, str] = field(default_factory=dict)
    _counters: dict[str, int] = field(default_factory=dict)

    def placeholder(self, kind: str, value: str) -> str:
        if value in self._forward:
            return self._forward[value]
        self._counters[kind] = self._counters.get(kind, 0) + 1
        token = f"[{kind}_{self._counters[kind]}]"
        self._forward[value] = token
        self._reverse[token] = value
        return token


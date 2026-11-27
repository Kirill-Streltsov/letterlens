"""Reversible pseudonymization of personal data before text reaches a model.

The model sees placeholders such as ``[IBAN_1]``. After the model call the
vault puts the original values back. The vault lives only in memory for the
duration of one pipeline step and is never stored or logged.

Limitations (documented in docs/security/data-protection.md): person names
are found in the address block and in greetings, by heuristics; every occurrence of a
found name is then replaced. Names that appear only elsewhere are not detected.
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
_NAME_WORD = r"[A-ZÄÖÜÇŞİ][\w'-]+"
# The leading name words of a line; OCR often appends noise ("Kirill Streltsov c 030").
_NAME_PREFIX = re.compile(rf"^({_NAME_WORD}(?:\s+{_NAME_WORD}){{1,3}})(?=\s|$|[,;])")
# Names in greetings: "Guten Tag Ayşe Yılmaz,", "Sehr geehrter Herr Demir".
_GREETING = re.compile(
    rf"(?i:guten\s+tag|sehr\s+geehrte[rs]?|hallo|liebe[rs]?)\s+(?:(?i:frau|herrn?)\s+)?"
    rf"({_NAME_WORD}(?:\s+{_NAME_WORD}){{0,3}})"
)
_NOT_NAMES = frozenset({"Damen", "Herren", "Kunde", "Kundin", "Mieter", "Mieterin", "Mitglied", "Eltern"})
_ORG_WORDS = re.compile(
    r"(?i)finanzamt|jobcenter|\bstadt\b|\bkreis\b|gmbh|\beg\b|kasse|behörde|amt\b|service|"
    r"versicherung|aok|barmer|dak|ikk|stadtwerke|inkasso|hausverwaltung|postfach|abteilung"
)


@dataclass
class PiiVault:
    """Holds placeholder-to-value mappings for one request."""

    _forward: dict[str, str] = field(default_factory=dict)
    _reverse: dict[str, str] = field(default_factory=dict)
    _counters: dict[str, int] = field(default_factory=dict)
    _name_res: list[tuple[re.Pattern[str], str]] = field(default_factory=list)

    def placeholder(self, kind: str, value: str) -> str:
        if value in self._forward:
            return self._forward[value]
        self._counters[kind] = self._counters.get(kind, 0) + 1
        token = f"[{kind}_{self._counters[kind]}]"
        self._forward[value] = token
        self._reverse[token] = value
        return token

    @property
    def size(self) -> int:
        return len(self._reverse)

    def counts(self) -> dict[str, int]:
        return dict(self._counters)

    def redact_text(self, text: str) -> str:
        for rule in RULES:
            text = _substitute(rule, text, self.placeholder)
        return text

    def redact_document(self, doc: LetterDocument) -> LetterDocument:
        texts = [line.text for line in doc.lines]
        address_lines, names = _address_block(texts)
        names += [n for n in _greeting_names(texts) if n not in names]
        name_patterns = self._name_patterns(names)
        self._name_res.extend(name_patterns)
        new_lines: list[OcrLine] = []
        for i, line in enumerate(doc.lines):
            if i in address_lines:
                text = self.placeholder("ADDRESS", line.text.strip())
            else:
                text = line.text
                for pattern, token in name_patterns:
                    text = pattern.sub(token, text)
                text = self.redact_text(text)
            new_lines.append(line.model_copy(update={"text": text}))
        return doc.model_copy(update={"lines": new_lines})

    def _name_patterns(self, names: list[str]) -> list[tuple[re.Pattern[str], str]]:
        """Every found name is replaced everywhere in the letter; the surname alone too."""
        patterns: list[tuple[re.Pattern[str], str]] = []
        for name in sorted(names, key=len, reverse=True):
            token = self.placeholder("NAME", name)
            patterns.append((re.compile(rf"(?<!\w){re.escape(name)}(?!\w)"), token))
            parts = name.split()
            if len(parts) > 1 and len(parts[-1]) >= 4:
                patterns.append((re.compile(rf"(?<!\w){re.escape(parts[-1])}(?!\w)"), token))
        return patterns

    def reapply(self, text: str) -> str:
        """Pseudonymize text that was restored earlier (for a second model call on the same letter).

        Uses the values this vault saw in redact_document: address lines, names (also the surname
        alone) and identifiers. Longest values first, so "Max Mustermann" wins over "Mustermann".
        """
        for value, token in sorted(self._forward.items(), key=lambda kv: len(kv[0]), reverse=True):
            text = re.sub(rf"(?<!\w){re.escape(value)}(?!\w)", token, text)
        for pattern, token in self._name_res:
            text = pattern.sub(token, text)
        return self.redact_text(text)

    def restore(self, value: Any) -> Any:
        """Replace placeholders in strings, lists, dicts and pydantic models."""
        if not self._reverse:
            return value
        if isinstance(value, str):
            return _PLACEHOLDER.sub(lambda m: self._reverse.get(m[0], m[0]), value)
        if isinstance(value, list):
            return [self.restore(v) for v in value]
        if isinstance(value, dict):
            return {k: self.restore(v) for k, v in value.items()}
        return value


_PLACEHOLDER = re.compile(r"\[[A-Z]+_\d+\]")


def _substitute(rule: Rule, text: str, make: Callable[[str, str], str]) -> str:
    def repl(match: re.Match[str]) -> str:
        if rule.group == 0:
            return make(rule.kind, match[0])
        start, end = match.span(rule.group)
        whole_start = match.start()
        token = make(rule.kind, match[rule.group])
        prefix = match[0][: start - whole_start]
        suffix = match[0][end - whole_start :]
        return f"{prefix}{token}{suffix}"

    return rule.pattern.sub(repl, text)


def _address_block(texts: list[str]) -> tuple[set[int], list[str]]:
    """Find the recipient's street line and name above a postcode line.

    Returns the indexes of street lines (replaced as a whole) and the names found.
    """
    address: set[int] = set()
    names: list[str] = []
    for i, text in enumerate(texts[:30]):
        if i < 2 or not _POSTCODE_CITY.match(text.strip()):
            continue
        street, name_line = texts[i - 1].strip(), texts[i - 2].strip()
        if not _STREET.match(street) or _ORG_WORDS.search(street):
            continue
        address.add(i - 1)
        match = _NAME_PREFIX.match(name_line)
        if match and not _ORG_WORDS.search(name_line) and match[1] not in names:
            names.append(match[1])
    return address, names


def _greeting_names(texts: list[str]) -> list[str]:
    found: list[str] = []
    for text in texts[:60]:
        for match in _GREETING.finditer(text):
            words = [w for w in match[1].split() if w not in _NOT_NAMES]
            name = " ".join(words)
            if len(name) >= 3 and name not in found and not _ORG_WORDS.search(name):
                found.append(name)
    return found


def scrub_for_logs(text: str, limit: int = 200) -> str:
    """Irreversible redaction for log lines. Use it on every free text that may reach a log."""
    vault = PiiVault()
    redacted = vault.redact_text(text)
    redacted = re.sub(r"\d{3,}", "<num>", redacted)
    return redacted[:limit]

"""Load the curated explanation corpus (backend/corpus/*.md)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

import yaml

from letterlens.domain import LetterType

CORPUS_DIR = Path(__file__).resolve().parents[3] / "corpus"
# Inside the Lambda bundle the corpus is copied next to the package.
_BUNDLED_DIR = Path(__file__).resolve().parents[1] / "corpus"


@dataclass(frozen=True, slots=True)
class CorpusEntry:
    id: str
    title: str
    letter_types: frozenset[LetterType]
    source_name: str
    source_url: str
    checked_on: date
    text: str
    reviewed_by: str | None
    keywords_de: tuple[str, ...] = ()

    def searchable(self) -> str:
        # German keywords bridge the German letter and the English passage text.
        return f"{self.title}\n{' '.join(self.keywords_de)}\n{self.text}"



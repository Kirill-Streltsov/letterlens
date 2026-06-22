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


def parse_entry(raw: str) -> CorpusEntry:
    _, front, body = raw.split("---\n", 2)
    meta = yaml.safe_load(front)
    return CorpusEntry(
        id=meta["id"],
        title=meta["title"],
        letter_types=frozenset(LetterType(t) for t in meta["letter_types"]),
        source_name=meta["source_name"],
        source_url=meta["source_url"],
        checked_on=meta["checked_on"],
        text=" ".join(body.split()),
        reviewed_by=meta.get("reviewed_by"),
        keywords_de=tuple(meta.get("keywords_de") or ()),
    )


def corpus_dir() -> Path:
    return _BUNDLED_DIR if _BUNDLED_DIR.is_dir() else CORPUS_DIR


@lru_cache(maxsize=1)
def load_corpus(directory: Path | None = None) -> tuple[CorpusEntry, ...]:
    folder = directory or corpus_dir()
    entries = [parse_entry(p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.md"))]
    ids = [e.id for e in entries]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate corpus ids")
    return tuple(entries)

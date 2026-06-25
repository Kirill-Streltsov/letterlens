"""Hybrid retrieval over the curated corpus.

The corpus is small (tens of passages), so the index lives in memory and is
built at cold start. Ranking: BM25 and (when available) embedding similarity,
fused with reciprocal rank fusion (RRF). Passages for other letter types are
filtered out. ADR-0004 explains why this is not pgvector.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from letterlens.domain import LetterType, Passage
from letterlens.ml.classifier import normalize_text
from letterlens.rag.corpus import CorpusEntry, load_corpus

INDEX_FILE = Path(__file__).with_name("artifacts") / "corpus_embeddings.json"
RRF_K = 60

_TOKEN = re.compile(r"[a-z]{3,}")
_STOP = frozenset(
    "the and for that this with are can from not was has have will must der die das und "
    "ist sie ihr ihre den dem des ein eine einer von mit auf bis zum zur nach bei wir uns "
    "oder auch werden wird sind".split()
)

Embedder = Callable[[list[str]], list[list[float]]]


def tokenize(text: str) -> list[str]:
    tokens = [t for t in _TOKEN.findall(normalize_text(text)) if t not in _STOP]
    # Crude German compound support: also index 6-char prefixes of long words.
    return tokens + [t[:6] for t in tokens if len(t) > 9]


class Bm25:
    def __init__(self, docs: Sequence[str], k1: float = 1.4, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(d)) for d in docs]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.lengths) / max(len(self.docs), 1)
        df: Counter[str] = Counter()
        for doc in self.docs:
            df.update(doc.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for doc, length in zip(self.docs, self.lengths, strict=True):
            score = 0.0
            for term in terms:
                tf = doc.get(term, 0)
                if tf:
                    norm = tf + self.k1 * (1 - self.b + self.b * length / self.avg)
                    score += self.idf[term] * tf * (self.k1 + 1) / norm
            out.append(score)
        return out


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


@dataclass(frozen=True)
class EmbeddingIndex:
    model: str
    vectors: dict[str, list[float]]

    @classmethod
    def load(cls, path: Path = INDEX_FILE) -> EmbeddingIndex | None:
        if not path.exists():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(model=raw["model"], vectors=raw["vectors"])


class HybridRetriever:
    def __init__(
        self,
        entries: Sequence[CorpusEntry] | None = None,
        index: EmbeddingIndex | None = None,
        embedder: Embedder | None = None,
    ) -> None:
        self.entries = list(entries if entries is not None else load_corpus())
        self.bm25 = Bm25([e.searchable() for e in self.entries])
        self.index = index
        self.embedder = embedder

    def _dense_ranks(self, query: str, candidates: list[int]) -> dict[int, int]:
        if self.index is None or self.embedder is None:
            return {}
        try:
            [qvec] = self.embedder([query])
        except Exception:  # noqa: BLE001 - dense retrieval is optional; BM25 still works
            return {}
        scored = [
            (i, cosine(qvec, self.index.vectors[self.entries[i].id]))
            for i in candidates
            if self.entries[i].id in self.index.vectors
        ]
        scored.sort(key=lambda item: item[1], reverse=True)
        return {i: rank for rank, (i, _) in enumerate(scored)}

    def search(self, query: str, letter_type: LetterType, k: int = 4) -> list[Passage]:
        candidates = [
            i
            for i, e in enumerate(self.entries)
            if letter_type in e.letter_types or letter_type is LetterType.OTHER
        ]
        if not candidates:
            return []
        bm25 = self.bm25.scores(query)
        sparse = sorted(candidates, key=lambda i: bm25[i], reverse=True)
        sparse_ranks = {i: rank for rank, i in enumerate(sparse)}
        dense_ranks = self._dense_ranks(query, candidates)


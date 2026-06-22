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



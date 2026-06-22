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


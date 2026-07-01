"""Letter-type classifier: TF-IDF + multinomial logistic regression + temperature scaling.

Training uses scikit-learn (scripts/train_classifier.py). Serving uses this
dependency-free implementation, so the Lambda bundle needs no numpy or scipy.
tests/test_classifier_parity.py proves that both give the same probabilities.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from letterlens.domain import Classification, LetterType

ARTIFACT = Path(__file__).with_name("artifacts") / "letter_type.json"
ABSTAIN_BELOW = 0.5

_FOLD = str.maketrans({"ä": "a", "ö": "o", "ü": "u", "ß": "ss", "é": "e"})
_WORD = re.compile(r"[a-z]{2,}")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower().translate(_FOLD)
    return re.sub(r"\d", "0", text)


def analyze(text: str) -> list[str]:
    """Feature extractor shared by training and serving. Do not change without retraining."""
    words = _WORD.findall(normalize_text(text))
    features = [f"w:{w}" for w in words]
    features += [f"b:{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
    for word in words:
        padded = f" {word} "
        if len(padded) >= 4:
            features += [f"c:{padded[i : i + 4]}" for i in range(len(padded) - 3)]
    return features


@dataclass(frozen=True)
class LinearModel:
    version: str
    classes: list[str]
    idf: dict[str, float]
    weights: dict[str, list[float]]
    intercept: list[float]
    temperature: float

    def logits(self, text: str) -> list[float]:
        counts = Counter(f for f in analyze(text) if f in self.idf)
        vector = {f: (1.0 + math.log(c)) * self.idf[f] for f, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vector.values())) or 1.0
        out = list(self.intercept)
        for feature, value in vector.items():
            for k, w in enumerate(self.weights[feature]):
                out[k] += w * value / norm
        return out

    def predict_proba(self, text: str, temperature: float | None = None) -> list[float]:
        t = self.temperature if temperature is None else temperature
        scaled = [z / t for z in self.logits(text)]
        top = max(scaled)
        exps = [math.exp(z - top) for z in scaled]
        total = sum(exps)
        return [e / total for e in exps]


"""Train the letter-type classifier and export it for dependency-free serving.

Usage: uv run python scripts/train_classifier.py [--per-template 60]

Outputs
  src/letterlens/ml/artifacts/letter_type.json  model for serving
  evals/reports/classifier.json                 metrics (leave-one-template-out, calibration)
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, log_loss

from letterlens.ml.classifier import ARTIFACT, analyze
from letterlens.synthetic import generate_corpus
from letterlens.synthetic.generator import TEMPLATES
from letterlens.synthetic.lexicon import lexicon_documents

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "evals" / "reports" / "classifier.json"
CLASSES = [t.value for t in TEMPLATES]
LEXICON_GROUP = "lexicon"


def build_dataset(per_template: int, seed: int) -> tuple[list[str], list[str], list[str]]:
    texts, labels, groups = [], [], []
    for noise in (0.0, 0.15):
        for letter in generate_corpus(per_template, seed=seed + int(noise * 100), noise=noise):
            texts.append("\n".join(letter.lines))
            labels.append(letter.letter_type)
            groups.append(letter.template_id)
    # Lexicon documents are domain knowledge. They are never held out.
    for text, label in lexicon_documents(per_template * 3, seed):
        texts.append(text)
        labels.append(label)
        groups.append(LEXICON_GROUP)
    return texts, labels, groups


def make_vectorizer() -> TfidfVectorizer:
    return TfidfVectorizer(
        analyzer=analyze, sublinear_tf=True, min_df=2, max_features=30_000, norm="l2"
    )



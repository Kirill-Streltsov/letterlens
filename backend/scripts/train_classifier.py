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


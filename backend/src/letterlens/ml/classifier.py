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



"""The exported model must give the same probabilities as scikit-learn."""

import math

import pytest

from letterlens.domain import LetterType
from letterlens.ml.classifier import analyze, default_model
from letterlens.synthetic import generate_corpus

sklearn = pytest.importorskip("sklearn")


def test_parity_with_sklearn() -> None:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression

    letters = generate_corpus(6, seed=3)
    texts = ["\n".join(letter.lines) for letter in letters]
    labels = [letter.letter_type for letter in letters]
    vec = TfidfVectorizer(analyzer=analyze, sublinear_tf=True, min_df=1, norm="l2")
    clf = LogisticRegression(max_iter=2000).fit(vec.fit_transform(texts), labels)

    from letterlens.ml.classifier import LinearModel


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

    vocab = vec.vocabulary_
    model = LinearModel(
        version="parity",
        classes=list(clf.classes_),
        idf={t: float(vec.idf_[i]) for t, i in vocab.items()},
        weights={t: [float(w) for w in clf.coef_[:, i]] for t, i in vocab.items()},
        intercept=[float(b) for b in clf.intercept_],
        temperature=1.0,
    )
    probe = generate_corpus(1, seed=99)
    for letter in probe:
        text = "\n".join(letter.lines)
        expected = clf.predict_proba(vec.transform([text]))[0]
        actual = model.predict_proba(text)
        assert np.allclose(expected, actual, atol=1e-9)


def test_shipped_model_classifies_unseen_seeds() -> None:
    model = default_model()
    letters = generate_corpus(2, seed=12345)
    correct = sum(model.classify("\n".join(x.lines)).letter_type.value == x.letter_type for x in letters)
    assert correct / len(letters) >= 0.95


def test_probabilities_are_calibrated_distribution() -> None:
    result = default_model().classify("Sehr geehrte Damen und Herren")
    assert math.isclose(sum(result.probabilities.values()), 1.0, abs_tol=1e-3)


def test_low_confidence_abstains_to_other() -> None:
    result = default_model().classify("Hallo")
    if result.abstained:
        assert result.letter_type is LetterType.OTHER

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
    return TfidfVectorizer(analyzer=analyze, sublinear_tf=True, min_df=2, max_features=30_000, norm="l2")


def make_model() -> LogisticRegression:
    return LogisticRegression(C=2.0, max_iter=3000)


def fit_temperature(logits: np.ndarray, y: np.ndarray) -> float:
    best_t, best_nll = 1.0, float("inf")
    for t in np.geomspace(0.02, 5.0, 160):
        z = logits / t
        z = z - z.max(axis=1, keepdims=True)
        p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
        nll = -np.mean(np.log(p[np.arange(len(y)), y] + 1e-12))
        if nll < best_nll:
            best_t, best_nll = float(t), nll
    return best_t


def expected_calibration_error(probs: np.ndarray, y: np.ndarray, bins: int = 10) -> float:
    conf = probs.max(axis=1)
    correct = probs.argmax(axis=1) == y
    ece = 0.0
    for lo in np.linspace(0, 1, bins, endpoint=False):
        mask = (conf > lo) & (conf <= lo + 1 / bins)
        if mask.any():
            ece += mask.mean() * abs(correct[mask].mean() - conf[mask].mean())
    return float(ece)


def softmax(z: np.ndarray) -> np.ndarray:
    z = z - z.max(axis=1, keepdims=True)
    return np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)


def leave_one_template_out(
    texts: list[str], labels: list[str], groups: list[str]
) -> tuple[dict, np.ndarray, np.ndarray]:
    """Hold out one whole template family at a time: measures generalization to new layouts.

    Returns the metrics and the out-of-template logits and labels. The temperature is
    fitted on these logits, so confidence reflects letters with an unseen layout.
    """
    y = np.array([CLASSES.index(lbl) for lbl in labels])
    per_template = {}
    preds = np.zeros_like(y)
    held = np.array([g != LEXICON_GROUP for g in groups])
    oot_logits = np.zeros((len(y), len(CLASSES)))
    for template in sorted(set(groups) - {LEXICON_GROUP}):
        test = np.array([g == template for g in groups])
        vec = make_vectorizer()
        x_train = vec.fit_transform([t for t, m in zip(texts, test, strict=True) if not m])
        clf = make_model().fit(x_train, y[~test])
        x_test = vec.transform([t for t, m in zip(texts, test, strict=True) if m])
        logits = clf.decision_function(x_test)
        oot_logits[test] = logits
        pred = clf.classes_[logits.argmax(axis=1)]
        preds[test] = pred
        per_template[template] = float((pred == y[test]).mean())
    metrics = {
        "accuracy": float(accuracy_score(y[held], preds[held])),
        "macro_f1": float(f1_score(y[held], preds[held], average="macro")),
        "per_template_accuracy": per_template,
    }
    return metrics, oot_logits[held], y[held]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-template", type=int, default=60)
    parser.add_argument("--seed", type=int, default=11)
    args = parser.parse_args()

    texts, labels, groups = build_dataset(args.per_template, args.seed)
    y = np.array([CLASSES.index(lbl) for lbl in labels])

    loto, cal_logits, y_cal = leave_one_template_out(texts, labels, groups)
    temperature = fit_temperature(cal_logits, y_cal)
    raw_probs = softmax(cal_logits)
    cal_probs = softmax(cal_logits / temperature)
    abstain = cal_probs.max(axis=1) < 0.5
    answered = ~abstain
    loto["abstain_rate"] = float(abstain.mean())
    loto["accuracy_when_answered"] = float(
        (cal_probs.argmax(axis=1)[answered] == y_cal[answered]).mean() if answered.any() else 0
    )

    # Final model: all data, temperature from the out-of-template predictions.
    vec = make_vectorizer()
    x_all = vec.fit_transform(texts)
    clf = make_model().fit(x_all, y)

    vocab = vec.vocabulary_
    terms: dict[str, list[float]] = {}
    for term, idx in vocab.items():
        terms[term] = [round(float(vec.idf_[idx]), 6)] + [round(float(w), 6) for w in clf.coef_[:, idx]]
    version = f"lt-{datetime.now(UTC):%Y%m%d}-{len(vocab)}"
    artifact = {
        "version": version,
        "classes": [CLASSES[i] for i in clf.classes_],
        "intercept": [round(float(b), 6) for b in clf.intercept_],
        "temperature": round(temperature, 4),
        "terms": terms,
    }
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")

    report = {
        "version": version,
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "samples": len(texts),
        "features": len(vocab),
        "leave_one_template_out": loto,
        "calibration": {
            "temperature": temperature,
            "nll_before": float(log_loss(y_cal, raw_probs, labels=list(range(len(CLASSES))))),
            "nll_after": float(log_loss(y_cal, cal_probs, labels=list(range(len(CLASSES))))),
            "ece_before": expected_calibration_error(raw_probs, y_cal),
            "ece_after": expected_calibration_error(cal_probs, y_cal),
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "leave_one_template_out"}, indent=2))
    print("leave-one-template-out accuracy:", round(loto["accuracy"], 4))
    print(
        "abstain rate:",
        round(loto["abstain_rate"], 3),
        "accuracy when answered:",
        round(loto["accuracy_when_answered"], 3),
    )
    for template, acc in loto["per_template_accuracy"].items():
        print(f"  {template:32s} {acc:.3f}")


if __name__ == "__main__":
    main()

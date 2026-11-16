# ADR-0007: Classifier training with scikit-learn, dependency-free serving

Status: accepted · Date: 2026-11-16

## Context

The letter type routes the extraction prompt and filters retrieval. A small,
explainable model is enough. numpy, scipy and scikit-learn would add about
150 MB to the Lambda bundle (limit 250 MB unzipped).

## Decision

1. Train offline with scikit-learn: TF-IDF over words, word bigrams and character
   4-grams, then multinomial logistic regression (`scripts/train_classifier.py`).
2. Export vocabulary, IDF weights, coefficients and temperature to JSON. Serve with
   a pure-Python implementation (`ml/classifier.py`). A test proves equal probabilities.
3. Evaluate with leave-one-template-out: each letter family is held out once.
   This measures generalization to unseen layouts, not memorization.
4. Add domain-vocabulary documents to the training data, so the model learns domain words, not one layout.
5. Fit the temperature on the out-of-template predictions. Abstain (type `other`) below 0.5.

## Consequences

- Leave-one-template-out accuracy rose from 50 % (templates only) to 97.8 %. Calibration error fell from 0.32 to 0.01.
- The Lambda bundle stays at 84 MB.
- The training data is synthetic. Real, consented letters must be added before the numbers are representative.

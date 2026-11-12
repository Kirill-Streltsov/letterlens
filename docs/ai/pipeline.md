# AI pipeline

This document describes how LetterLens turns OCR text into verified facts and an
explanation. Code: `backend/src/letterlens/pipeline/steps.py`.

## 1. Input

The client sends a `LetterDocument`: text lines with `page`, `index`, optional
normalized bounding box and OCR confidence. Each line has the id `p{page}-l{index}`.
All facts and summary sentences refer to these ids.

## 2. Steps

### 2.1 Classify

- Model: TF-IDF + logistic regression, temperature-scaled ([ADR-0007](../architecture/adr/0007-classifier-training-and-serving.md)).
- Types: `tax`, `benefits`, `health_insurance`, `immigration`, `landlord`, `other`.
- Below confidence 0.5 the classifier abstains and returns `other`.
- The type selects the guidance block in the extraction prompt and filters retrieval.

### 2.2 Extract


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

1. Remove lines that look like instructions to a model (`safety/guardrail.py`, `neutralize_injections`).
2. Pseudonymize personal data (`safety/pii.py`): IBAN, e-mail, phone, tax id, tax number,
   BG number, insurance number, birth date, case references, and the recipient name and
   street in the address block. The model sees placeholders such as `[TAXNO_1]`.
3. Call the gateway with task `extract`, the prompt `extract_system(letter_type)` and the strict schema `Extraction`.
4. Put the original values back into the result (`PiiVault.restore`).
5. If the gateway fails or a budget is spent, use the rule-based extractor (`extraction/rules.py`) and mark the letter `degraded`.

### 2.3 Verify

The verifier (`grounding/verifier.py`) sets the trust state of each fact:

| Situation | State | Note shown to the reader |
|---|---|---|
| The cited line contains the date or amount | `verified` | none |
| The value is in another line | `needs_check` | "appears in the letter, but not in the quoted line" |
| The value is not in the letter | `needs_check` | "not found in the quoted line" |
| A date before the letter date | `needs_check` | "before the letter date" |
| A relative period | `needs_check`, estimated | the rule, for example "1 months; received on 2026-03-16 …" |

Reference numbers that are not in the cited line are removed.

### 2.4 Retrieve

Query: subject, sender, deadline and action descriptions, and the first 2,500
characters of the letter (German terms such as "Widerspruch" carry most signal).
Ranking: BM25 over title, German keywords and text; embeddings when an index for
the configured model exists; reciprocal rank fusion; filter by letter type; drop
passages without any lexical or dense match. Result: up to 4 passages `c1`…`c4`.


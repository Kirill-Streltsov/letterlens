# Evaluation

Every change to a prompt, a model, a parser or the corpus is measured. The release
gate (`backend/evals/thresholds.yaml`) blocks a change that fails a threshold.

## 1. Data

| Set | Size | Source | Labels |
|---|---|---|---|
| Golden letters | 126 | 95 synthetic letters (19 template families, unseen seeds), 19 OCR-noise variants, 12 hand-written letters with layouts that no template uses (one is a prompt-injection letter) | sender, letter date, references, every deadline (explicit or relative), every amount with direction |
| Red-team questions | 96 | 54 requests for individual legal advice and 34 general questions in English, German, Turkish, Arabic, Ukrainian and Russian; 8 injection attempts | advice / benign / injection |
| Retrieval labels | 114 letters | expected corpus passages per letter family (`EXPECTED_PASSAGES` in `evals/run.py`) | relevant passage ids |
| Judge calibration | 20 pairs | controlled perturbations of reference summaries (changed date, amount, obligation) | faithful / unfaithful |

The synthetic generator (`letterlens/synthetic/generator.py`) is deterministic.
`python -m evals.run --rebuild-golden` rebuilds the set.

> The golden set is synthetic and hand-written. Before a public launch, add real,
> consented and anonymized letters (target: 100). Keep them out of git if the
> consent requires it; the runner reads any JSONL file in the same format.

## 2. Suites and metrics

| Suite | Metric | Meaning |
|---|---|---|
| classification | synthetic and hand-written accuracy, macro recall, expected calibration error (ECE) | Does routing work, and is the confidence honest? |
| extraction | **unsafe verified dates / amounts** | Facts shown as verified that are not in the labels. Must be 0. |
| extraction | explicit deadline recall and precision, exact match per letter | Are all deadlines found, and no extra ones? |
| extraction | letter date accuracy, relative deadline recall, amount recall, direction accuracy | Completeness of the facts |
| retrieval | recall@4, MRR | Is a relevant passage in the context? |
| guardrail | advice catch rate (rules only and combined), benign false-positive rate, injection catch rate, per language | Does the legal boundary hold without blocking normal questions? |
| faithfulness (live) | judge accuracy on the calibration set; mean judge score per language | Does the translation keep the facts? |

## 3. Profiles

| Profile | Provider | When | Command |
|---|---|---|---|
| offline | deterministic rules (`fake`) | every pull request | `python -m evals.run` |
| chaos | rules + fault injection: 35 % of dates shifted, amounts changed, citations wrong | every pull request | `python -m evals.run --profile chaos` |
| live | the configured model | before a release; after a prompt or model change | `python -m evals.run --profile live` |

## 4. Current results

Offline profile (rules baseline). Report: `backend/evals/reports/offline.md`.

| Metric | Value | Gate |
|---|---|---|
| unsafe verified dates / amounts | 0 / 0 | max 0 |
| explicit deadline recall / precision | 0.980 / 0.941 | min 0.85 / – |
| letter date accuracy | 1.000 | min 0.95 |
| amount recall / direction accuracy | 1.000 / 0.934 | min 0.90 / – |
| classification, synthetic / hand-written | 1.000 / 0.917 | min 0.95 / 0.75 |
| classification ECE | 0.007 | max 0.10 |
| retrieval recall@4 | 0.991 | min 0.85 |
| advice catch rate / false positives | 0.852 / 0.000 | min 0.85 / max 0.05 |
| injection catch rate | 1.000 | min 0.90 |

Chaos profile: 91 errors injected, **0** shown as verified. The grounding rate
drops to 0.62, so the reader sees "please check" on the affected facts.

Classifier training report (`backend/evals/reports/classifier.json`):
leave-one-template-out accuracy 0.978; ECE 0.322 before and 0.010 after temperature scaling.

## 5. The gate blocks bad changes

`backend/tests/test_eval_gate.py` simulates a pull request that makes the verifier
trust the model. With fault injection, wrong dates then reach the reader as facts,
and `check_gates` fails on `unsafe_verified_dates` and `unsafe_verified_amounts`.
This test runs in CI.

## 6. The judge

The faithfulness suite back-translates each summary to English and asks a judge
model to compare it with the English reference (score 1 to 5). Before the scores
count, the judge must classify the calibration pairs correctly (min 0.90). Add
pairs labelled by bilingual reviewers to `evals/judge_calibration/reviewed.jsonl`
(fields `reference`, `candidate`, `faithful`).

`--update-languages` writes the scores to `languages.yaml`. A language is `enabled`
at a score of 0.80 or more with a validated judge; otherwise it is `experimental`,
and the clients show "beta".

## 7. How to add a case

1. Write the letter as a `SyntheticLetter` in `evals/handwritten.py`, with all labels.
2. Run `python -m evals.run --rebuild-golden`.
3. If the case shows a defect, fix the code, not the label.

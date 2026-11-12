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


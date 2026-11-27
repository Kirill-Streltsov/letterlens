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
| faithfulness (live) | judge accuracy on the calibration set; mean judge score per language; share of translations with one sentence per English sentence; judge issues for scores below 4 | Does the translation keep the facts and every sentence? |
| completeness (live) | key-point recall on hand-written letters; judge false-positive rate on an empty summary | Does the summary contain what matters most (decision, conditions, consequences, actions, permissions)? |

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

Live profile (Mistral: `mistral-small-latest` for extraction and the guard,
`mistral-medium-latest` for explanations and translations; prompts `extract-v5`, `explain-v6`, `translate-explanation-v1`; 27 November 2026; 532 calls; 0.12 USD
list price; report `backend/evals/reports/live.md`):

| Metric | Value | Gate |
|---|---|---|
| unsafe verified dates / amounts | 0 / 0 | max 0 |
| degraded letters (model failed, rules used) | 0 | max 0 |
| explicit deadline recall / precision | 0.990 / 1.000 | min 0.95 / 0.95 |
| letters with every deadline exact | 0.993 | – |
| letter date accuracy / amount recall / direction | 0.993 / 0.988 / 0.988 | min 0.97 / 0.95 / 0.90 |
| advice catch rate (rules + model) / false positives | 1.000 / 0.000 | min 0.95 / max 0.10 |
| injection catch rate | 1.000 | min 0.95 |
| judge accuracy on the calibration set | 0.95 | min 0.90 |
| faithfulness de / tr / ar / uk / ru | 0.975 / 0.925 / 1.00 / 0.975 / 0.95 | min 0.80 to enable |
| translations aligned (one sentence per English sentence) | 1.000 | min 0.95 |
| key-point recall / judge false positives | 0.895 / 0.000 | min 0.80 / max 0.10 |

History of the translation results:

| Design | Faithfulness (de / tr / ar / uk / ru) | Aligned |
|---|---|---|
| `explain-v4`, each language written from the letter | 0.95 / 0.925 / 0.95 / 0.90 / 0.975 | – |
| `explain-v5`, each language written from the letter | 0.825 / 0.90 / 0.875 / 0.75 / 0.80 | – |
| `explain-v5` + translation of the checked English text | 0.975 / 0.95 / 1.00 / 1.00 / 0.95 | 1.000 |

With `explain-v5`, every language was written separately from the letter, so the
languages could differ in content, and the judge counted these differences. Now the
English explanation is checked once and translated item by item (`docs/ai/pipeline.md`,
section 2.6). The judge reasons (`low_scores`) also showed two measurement and safety
defects, both fixed:

- The number check split amounts like "1 092,50" (space as thousands separator in
  Ukrainian and Russian) and dropped correct sentences. 6 of 40 translations lost a
  sentence with an amount. The new `aligned_share` gate finds such losses.
- The back-translation chose "recalculate" for Ukrainian "перерахувати" (also
  "transfer money"). `backtranslate-v2` chooses the meaning that fits official letters.

Key-point recall varies between runs of the same prompt (0.895, 0.947 and 0.895): the English
summary sometimes leaves out the general work permission in the study letter.
Other weaknesses: in earlier runs the model guard refused about 3 % of normal questions (0 % in the last run).

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

## 8. Real and sample letters

Synthetic letters show that the mechanisms work. Real documents show what the
synthetic set misses. On 27 November 2026 the pipeline ran on 31 public documents:

| Source | Documents |
|---|---|
| Official sample notices (Finanzverwaltung NRW, ZBFS Bayern, Ministerialblatt NRW, Amtsblatt Sachsen, Bavarian model texts) | tax assessments, Familienkasse rejection, warning and hearing form, enforcement notice, model remedy texts |
| Real letters from authorities, published with redactions on FragDenStaat | objection decisions and replies of the BMAS, BfDI, Jobcenter Berlin Neukölln, LDA Brandenburg |
| Jobcenter publications | information sheet (Würzburg), staff guidance (Wuppertal), internal circular (Gera) |
| Sample letters of associations and publishers | fine notice, rent increases (Haus & Grund), utility statements, notice of termination |
| Blank court forms | enforcement order (Vollstreckungsbescheid) |

Method: `tools/review/ocr.swift` reads each PDF with Apple Vision (the same OCR as the
iOS app, including its errors); `backend/scripts/review_letters.py` runs the live
pipeline and prints the facts, the summary and every sentence that the checks dropped.
A person reviewed every result. The documents and results are not in the repository:
some are protected by copyright, and real letters can contain personal data.

| Finding | Fix | Test |
|---|---|---|
| A fine notice, a hearing form and a court form were classified as "benefits" (p ≥ 0.88) | Court and fine vocabulary; template `traffic_fine`; retrained classifier | golden set, `traffic_fine` |
| No passage for fines, so next steps cited tax and benefits passages | Passage 27 (§§ 56, 67, 111 OWiG; § 25 StVG) | retrieval suite |
| A placeholder date ("bis zum TT.MM.2015") became 1 November 2015 | Dates that are nowhere in the letter are never shown | `test_placeholder_date_is_not_shown` |
| The model computed "two weeks after delivery" itself; no rule was shown | Such dates are recomputed with the documented rule; formal delivery gets an envelope note | `test_computed_date_is_replaced_by_the_documented_estimate` |
| Blank fields ("_ EUR") and percentages became 0.00 or 0.01 EUR | Amounts that are nowhere in the letter are dropped | `test_amount_from_a_blank_field_is_dropped` |
| OCR read "380,00 EUR" as "380, 00 EUR"; tax tables have no currency sign per value | OCR repair; strict German money format accepted in the cited line | `test_ocr_space_after_decimal_comma_and_table_amounts_are_verified` |
| Assessed and withheld tax was shown as "to pay" | Prompt rule; code correction for "Festgesetzt werden", "ab Steuerabzug", "bereits gezahlt" lines | `test_assessed_and_withheld_amounts_are_not_to_pay` |
| Guides and internal circulars were explained as letters with tasks for the reader | Prompt rule (extract-v5, explain-v6); the rules fallback ignores internal circulars | hand-written `staff-circular` |
| Amounts like "1 092,50" in Ukrainian and Russian translations were dropped | Space thousands separator accepted | `test_amounts_with_space_thousands_separator_are_recognized` |

Four hand-written cases keep these findings in the golden set: `fine-ocr-spacing`,
`tax-table`, `blank-template` and `staff-circular`.

Known limits after this round: for guides and blank forms the model still sometimes lists
tasks for other people (for example a landlord's duties in a landlord guide), although
the headline says what the document is. The classifier has no type for freedom-of-information
letters and files them under "benefits".

Repeat the review after a model or prompt change:

```bash
swiftc -O -o /tmp/ocr tools/review/ocr.swift
/tmp/ocr letter.pdf > letter.txt
cd backend && PYTHONPATH=. uv run python scripts/review_letters.py --lang uk letter.txt
```

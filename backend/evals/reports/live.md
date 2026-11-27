# Evaluation report: profile `live`

Provider: `mistral`. Prompts: `['extract-v4', 'explain-v5', 'translate-explanation-v1', 'guard-v2', 'backtranslate-v2']`.

## classification

| Metric | Value |
|---|---|
| synthetic_accuracy | 1.0 |
| handwritten_accuracy | 0.9230769230769231 |
| macro_recall | 0.9920634920634921 |
| ece | 0.0067 |
| model_version | lt-20261126-8426 |

## extraction

| Metric | Value |
|---|---|
| letters | 127 |
| letter_date_accuracy | 0.9921 |
| explicit_deadline_recall | 1.0 |
| explicit_deadline_precision | 0.9899 |
| deadline_exact_match_letters | 0.9921 |
| relative_deadline_recall | 1.0 |
| amount_recall | 1.0 |
| amount_direction_accuracy | 0.9781 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.9899 |
| mean_grounding_rate | 0.9974 |
| degraded_letters | 0 |

## retrieval

| Metric | Value |
|---|---|
| letters | 115 |
| recall_at_4 | 0.9913 |
| mrr | 0.9913 |

## guardrail

| Metric | Value |
|---|---|
| questions | 96 |
| advice_catch_rate | 1.0 |
| advice_catch_rate_rules_only | 0.8519 |
| benign_false_positive_rate | 0.0294 |
| injection_catch_rate | 1.0 |

## faithfulness

| Metric | Value |
|---|---|
| judge_accuracy_on_calibration_set | 0.95 |
| letters | 8 |
| min_language_score | 0.95 |
| aligned_share | 1.0 |

## completeness

| Metric | Value |
|---|---|
| letters | 5 |
| keypoint_recall | 0.8947 |
| judge_false_positive_rate | 0.0 |

## Gate

- PASS: all gates

# Evaluation report: profile `live`

Provider: `mistral`. Prompts: `['extract-v5', 'explain-v6', 'translate-explanation-v1', 'guard-v2', 'backtranslate-v2']`.

## classification

| Metric | Value |
|---|---|
| synthetic_accuracy | 1.0 |
| handwritten_accuracy | 1.0 |
| macro_recall | 1.0 |
| ece | 0.0 |
| model_version | lt-20261127-8582 |

## extraction

| Metric | Value |
|---|---|
| letters | 137 |
| letter_date_accuracy | 0.9927 |
| explicit_deadline_recall | 0.9899 |
| explicit_deadline_precision | 1.0 |
| deadline_exact_match_letters | 0.9927 |
| relative_deadline_recall | 0.9762 |
| amount_recall | 0.9763 |
| amount_direction_accuracy | 0.9939 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 1.0 |
| mean_grounding_rate | 1.0 |
| degraded_letters | 0 |

## retrieval

| Metric | Value |
|---|---|
| letters | 123 |
| recall_at_4 | 0.9919 |
| mrr | 0.9919 |

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
| keypoint_recall | 1.0 |
| judge_false_positive_rate | 0.0 |

## Gate

- PASS: all gates

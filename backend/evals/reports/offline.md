# Evaluation report: profile `offline`

Provider: `fake`. Prompts: `['extract-v5', 'explain-v6', 'translate-explanation-v1', 'guard-v2', 'backtranslate-v2']`.

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
| explicit_deadline_recall | 0.9798 |
| explicit_deadline_precision | 0.9417 |
| deadline_exact_match_letters | 0.9416 |
| relative_deadline_recall | 1.0 |
| amount_recall | 0.9822 |
| amount_direction_accuracy | 0.9337 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.9417 |
| mean_grounding_rate | 0.9891 |
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
| advice_catch_rate | 0.8519 |
| advice_catch_rate_rules_only | 0.8519 |
| benign_false_positive_rate | 0.0 |
| injection_catch_rate | 1.0 |

## Gate

- PASS: all gates

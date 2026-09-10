# Evaluation report: profile `chaos`

Provider: `chaos`. Prompts: `['extract-v3', 'explain-v3', 'guard-v2']`.

## extraction

| Metric | Value |
|---|---|
| letters | 126 |
| letter_date_accuracy | 0.9683 |
| explicit_deadline_recall | 0.551 |
| explicit_deadline_precision | 0.5294 |
| deadline_exact_match_letters | 0.6032 |
| relative_deadline_recall | 1.0 |
| amount_recall | 0.6569 |
| amount_direction_accuracy | 0.9333 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.5294 |
| mean_grounding_rate | 0.6235 |
| injected_errors | 91 |

## Gate

- PASS: all gates

# Evaluation report: profile `chaos`

Provider: `chaos`. Prompts: `['extract-v3', 'explain-v3', 'guard-v2']`.

## extraction

| Metric | Value |
|---|---|
| letters | 126 |
| letter_date_accuracy | 1.0 |
| explicit_deadline_recall | 0.5612 |
| explicit_deadline_precision | 0.5392 |
| deadline_exact_match_letters | 0.6111 |
| relative_deadline_recall | 1.0 |
| amount_recall | 0.6496 |
| amount_direction_accuracy | 0.9101 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.5392 |
| mean_grounding_rate | 0.6167 |
| injected_errors | 91 |

## Gate

- PASS: all gates

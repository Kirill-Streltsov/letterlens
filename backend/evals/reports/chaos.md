# Evaluation report: profile `chaos`

Provider: `chaos`. Prompts: `['extract-v5', 'explain-v6', 'translate-explanation-v1', 'guard-v2', 'backtranslate-v2']`.

## extraction

| Metric | Value |
|---|---|
| letters | 137 |
| letter_date_accuracy | 0.9927 |
| explicit_deadline_recall | 0.5556 |
| explicit_deadline_precision | 0.9322 |
| deadline_exact_match_letters | 0.6496 |
| relative_deadline_recall | 1.0 |
| amount_recall | 0.6686 |
| amount_direction_accuracy | 0.9204 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.9322 |
| mean_grounding_rate | 0.7106 |
| degraded_letters | 0 |
| injected_errors | 97 |

## Gate

- PASS: all gates

# Evaluation report: profile `offline`

Provider: `fake`. Prompts: `['extract-v3', 'explain-v3', 'guard-v2']`.

## classification

| Metric | Value |
|---|---|
| synthetic_accuracy | 1.0 |
| handwritten_accuracy | 0.9166666666666666 |
| macro_recall | 0.9920634920634921 |
| ece | 0.0068 |
| model_version | lt-20261126-8426 |

## extraction

| Metric | Value |
|---|---|
| letters | 126 |
| letter_date_accuracy | 0.9683 |
| explicit_deadline_recall | 0.9796 |
| explicit_deadline_precision | 0.9412 |
| deadline_exact_match_letters | 0.9365 |
| relative_deadline_recall | 1.0 |
| amount_recall | 1.0 |
| amount_direction_accuracy | 0.9343 |
| unsafe_verified_dates | 0 |
| unsafe_verified_amounts | 0 |
| verified_share_of_dates | 0.9412 |
| mean_grounding_rate | 0.9881 |


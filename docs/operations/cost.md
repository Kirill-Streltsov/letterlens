# Cost model

Target: 0 EUR per month during the pilot. The table shows the free limits and
the volume at which each service starts to cost money.

## Free limits (checked 19 November 2026)

| Service | Free limit | LetterLens use per letter | Free capacity |
|---|---|---|---|
| Step Functions Standard | 4,000 state transitions per month (always free) | about 9 transitions | about **400 letters per month**; this is the first limit |
| Lambda | 1 M requests and 400,000 GB-seconds per month (always free) | about 12 invocations, 15 GB-s | far above 400 letters |
| CloudFront | 1 TB and 10 M requests per month (always free) | a few requests | far above |
| Cognito Lite | free up to the free-tier MAU limit | — | pilot scale |
| S3 | very small storage (only consented images) | 0 to 3 MB | cents at most |
| SSM Parameter Store | standard parameters free | — | — |
| CloudWatch | 5 GB logs, 10 custom metrics, 10 alarms | small JSON lines; 9 metrics; 6 alarms | inside |
| Neon free plan | 1 GB storage, 100 compute hours per month, scale to zero | a few KB per letter | about 100,000 letters of storage |
| Mistral free plan | rate-limited, free | 2 to 4 model calls | depends on current rate limits |

AWS free-plan accounts created after 15 July 2025 also get credits for the first
months. The design does not depend on them.

## Unit economics at scale (list prices)

The cost ledger records the list price of each call, also on free tiers.
Estimate per letter with Mistral list prices: extraction about 2,000 input and
800 output tokens on `mistral-small`, explanation about 3,000 input and 900
output tokens on `mistral-medium`: approximately 0.003 USD. With Claude Opus 5.5
($4 / $20 per million tokens): approximately 0.06 USD.

| Volume | AWS + Neon | Model (Mistral list price) |
|---|---|---|
| 300 letters per month | 0 EUR | 0 EUR on the free tier |
| 3,000 letters per month | about 1 EUR (27,000 transitions, of which 23,000 over the free limit, at 0.025 USD per 1,000) | about 9 USD on a paid plan |
| 30,000 letters per month | about 15 EUR, plus Neon Launch plan | about 90 USD |

Switch to Step Functions Express workflows above about 2,000 letters per month
(priced per request and duration, not per transition).

## Controls

- AWS Budget: e-mail at 50 % and 100 % of 1 USD actual spend and at 100 % forecast.
- Gateway: monthly model budget (`monthlyLlmBudgetUsd`) and daily tokens per user.
- Alarm `LlmSpendDaily`.
- Quotas: 3 letters per month on the free plan.

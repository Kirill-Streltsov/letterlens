# Data protection

This document supports the privacy policy and the data protection impact
assessment (DPIA, Art. 35 GDPR). A DPIA is necessary: the letters can contain
health data (Art. 9 GDPR) and data about residence status.

## 1. Data inventory

| Data | Source | Purpose | Storage | Retention |
|---|---|---|---|---|
| Letter text lines | Reader (OCR on device) | Explanation | Neon, encrypted per user | 30 days by default (Plus: up to 365), then deleted by the daily job |
| Letter images | Reader, only with consent | Counsellor sees the original | S3, encrypted | Deleted with the letter; lifecycle rule as backstop |
| Results (facts, explanations) | Pipeline | Display | Neon, encrypted per user | With the letter |
| Messages | Reader, counsellor | Counselling | Neon, encrypted with the reader's key | With the share or the account |
| Account | Cognito | Sign-in | Cognito (e-mail), Neon (subject id, plan, optional display name) | Until account deletion |
| Cost ledger | Gateway | Cost control | Neon, no content | 13 months, deleted by the daily job |
| Audit log | API | Accountability | Neon, no content | 3 years; the operator deletes older rows with the owner role (the app role cannot delete) |

LetterLens does not store the e-mail address in its own database.

## 2. Processors and transfers

| Processor | Function | Location | Note |
|---|---|---|---|
| Amazon Web Services EMEA SARL | Hosting, identity, storage | eu-central-1 (Frankfurt) | DPA in the AWS Service Terms |
| Neon Inc. | PostgreSQL | AWS eu-central-1 | US company: use the EU-US Data Privacy Framework or SCCs; content is encrypted before it reaches Neon |
| Mistral AI SAS | Model provider | EU | Turn off training on API data (deployment step 3) |
| Apple, Stripe | Payments | — | Only payment data; no letter content |


# API reference

The full contract is `contracts/openapi.json`. Locally, the interactive
documentation is at <http://localhost:8000/docs>. All routes start with `/v1`
and need `Authorization: Bearer <Cognito access token>`.

## Routes

| Method and path | Purpose |
|---|---|
| `GET /me`, `PATCH /me`, `DELETE /me`, `GET /me/export` | Profile, plan and usage; delete the account (crypto-shredding); export all data |
| `GET /languages` | Output languages and their status |
| `POST /letters` | Submit OCR lines. Header `Idempotency-Key` recommended. Returns 202. |
| `GET /letters`, `GET /letters/{id}?lang=` | List; letter with lines, facts and explanation |
| `POST /letters/{id}/explanations` | Explain in another language (asynchronous) |
| `PATCH /letters/{id}`, `DELETE /letters/{id}` | Retention period; delete |
| `POST /letters/{id}/images` | Pre-signed S3 uploads, with consent |
| `POST /letters/{id}/questions` | Question about the letter, with the legal-advice guardrail |
| `GET /counselling-services` | Public list of counselling services |
| `POST /letters/{id}/shares`, `DELETE /shares/{id}` | Share with consent; revoke |
| `GET`, `POST /shares/{id}/messages` | Messages, translated for the other side |
| `POST /invites/redeem` | Join a tenant with an invite code |
| `GET /counsellor/cases`, `GET`, `PATCH /counsellor/cases/{id}` | Case inbox, case, status |
| `POST /counsellor/translate` | Translation helper for replies |
| `GET /counsellor/tenants/{id}/stats`, `POST /counsellor/invites` | Statistics for funding reports; invites |
| `POST /billing/checkout`, `POST /billing/stripe/webhook` | Stripe |
| `POST /billing/appstore/transactions`, `POST /billing/appstore/notifications` | App Store |
| `GET /admin/costs`, `GET /admin/letters/{id}/cost` | Cost ledger |

## Errors

Every error has the body `{"code": "...", "message": "...", "request_id": "..."}`.

| Status | Code | Meaning |
|---|---|---|
| 400 | `language_unavailable`, `invalid_signature`, `consent_outdated` | Invalid input |
| 401 | `unauthorized` | No valid token |
| 402 | `quota_exceeded`, `plus_required` | Plan limit |
| 403 | `forbidden` | Role missing, or direct call without CloudFront |
| 404 | `not_found` | Does not exist or not visible to you (same answer on purpose) |
| 409 | `not_ready`, `share_revoked` | Wrong state |
| 422 | `invalid_request` | Schema validation failed; the message lists field paths, never values |
| 429 | `rate_limited` | Too many requests in one minute |
| 503 | `llm_unavailable` | Model not available for a synchronous request |

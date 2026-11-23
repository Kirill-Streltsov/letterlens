# Threat model

Method: STRIDE per trust boundary. Each threat has a mitigation and, where possible,
an automated test. Review this document when an interface or a processor changes.

## 1. Assets

| Asset | Sensitivity |
|---|---|
| Letter text and results | Very high: tax, health, residence, debts |
| Messages between reader and counsellor | Very high |
| Data keys (KEK in SSM, wrapped DEKs in the database) | Critical: they protect all of the above |
| Account data (token subject, plan, display name) | Medium |
| Cost ledger and audit log | Low (no content) |

## 2. Trust boundaries

1. Device → CloudFront → API (internet)
2. API / worker → Neon PostgreSQL (internet, TLS)
3. Worker → model provider (internet, TLS)
4. Reader ↔ counsellor (through shares)
5. Letter content → model (untrusted text inside the prompt)

## 3. Threats

| Id | Threat (STRIDE) | Mitigation | Evidence |
|---|---|---|---|
| T1 | A user reads another user's letter (I) | RLS on every table; the API sets the user per transaction; the app role cannot bypass RLS; ids are random UUIDs; foreign rows return 404 | `tests/test_rls.py`, `tests/test_api.py::test_other_users_get_404` |
| T2 | A counsellor reads letters that were not shared, or after revocation or expiry (I) | RLS checks an active share; revocation and expiry are tested; employers can never receive shares (trigger) | `test_rls.py`: revoked, expired, employer, forged tenant claim |
| T3 | Token forgery or replay (S) | Cognito RS256 access tokens; issuer, expiry, `token_use` and client id checked; JWKS cached | `tests/test_auth.py` |
| T4 | Dev authentication in production (S) | Settings refuse `auth_mode=dev` when `env=prod` | `test_auth.py::test_dev_mode_is_refused_in_prod` |
| T5 | Direct calls to the Lambda function URL bypass CloudFront (S, D) | Secret origin header, constant-time check | `test_api.py::test_origin_guard`, `infra/tests` |
| T6 | Prompt injection in a letter changes facts or advice (T) | Suspicious lines removed from prompts and never valid sources; strict schema; grounding check; output sanitizer | hand-written letter `hw-injection`, chaos profile |
| T7 | Abuse of quotas, model budget or free tier (D) | Rate limits per user and route; monthly letter quota; gateway spend and token budgets; daily spend alarm; AWS budget | `tests/test_gateway.py` budget tests |
| T8 | Personal data reaches the model provider (I) | On-device OCR; pseudonymization before the model; EU provider with training opt-out confirmed in config | `tests/test_pii.py`, `test_pipeline.py::test_llm_never_sees_recipient_name` |
| T9 | Personal data in logs (I) | Logs carry ids, routes, counters; validation errors do not echo input; provider errors do not echo bodies | `test_api.py::test_validation_error_does_not_echo_input` |
| T10 | Database copy or backup leaks (I) | Content is encrypted with per-user AES-256-GCM keys; the record id is the associated data; the KEK is outside the database | `tests/test_crypto.py` |
| T11 | Ciphertext moved between records (T) | Associated data binds ciphertext to the record id | `test_crypto.py::test_round_trip_and_aad_binding` |
| T12 | The model gives individual legal advice (E: legal risk) | Two-layer question guardrail, fail closed; output check; refusal and hand-over | red-team suite, [rdg-boundary.md](../legal/rdg-boundary.md) |
| T13 | Forged App Store or Stripe events grant Plus (S, T) | App Store JWS chain pinned to Apple Root CA G3 with OID checks; Stripe signature; idempotent event ids; app account token bound to the user | `tests/test_appstore.py`, `test_api.py::test_stripe_webhook_upgrades_plan_once` |
| T14 | Repudiation of shares, case views, deletions (R) | Append-only audit log (the app role has no UPDATE or DELETE) | `test_rls.py::test_audit_log_is_append_only` |
| T15 | Lost KEK makes data unreadable (D) | Documented backup of the KEK in the password manager; warning in the deployment guide | runbook |
| T16 | Supply-chain compromise in CI (T, E) | GitHub OIDC role limited to the CDK bootstrap roles and one environment; no stored AWS keys; locked dependency files | `infra/letterlens_infra/ci.py` |
| T17 | Cross-site scripting in the web app steals tokens (E) | React escaping; strict Content Security Policy at CloudFront; tokens in sessionStorage only | `infra` CSP |

## 4. Residual risks

- No WAF (ADR-0002). A large bot attack can use the free quotas. Response: the runbook alarm procedure; WAF is a one-construct upgrade.
- Names outside the address block are not pseudonymized. The provider is EU-based and has training turned off.
- The KEK is an SSM parameter, not a hardware key. Upgrade path: KMS customer-managed keys per tenant.
- An external penetration test has not been done. Do it before scaling beyond the pilot.

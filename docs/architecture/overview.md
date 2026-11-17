# Architecture overview

## 1. Purpose and constraints

LetterLens explains official German letters to people who are learning German.
The design follows from five constraints:

| Constraint | Effect on the design |
|---|---|
| A wrong deadline can harm a user. | The model proposes facts. Deterministic code verifies them. Unverified values are shown as "please check". |
| A legal assessment of an individual case is a regulated legal service (§ 2 RDG). | The product explains. A guardrail refuses individual advice and offers a counsellor. |
| Letters are among the most sensitive documents people own. | On-device OCR, pseudonymization before the model, per-user encryption, 30-day retention, EU processing. |
| The operating budget is 0 EUR. | Serverless always-free services, a free PostgreSQL, a free EU model tier. Paid upgrades are documented, not required. |
| One engineer builds and runs it. | A modular monolith: one Python package, one database, one deploy. |

## 2. Context

```mermaid
flowchart TB
  reader([Reader<br/>iOS or web]) --> LL[LetterLens]
  counsellor([Counsellor<br/>web]) --> LL
  LL --> mistral[Mistral API, EU<br/>model provider]
  LL --> neon[Neon PostgreSQL<br/>Frankfurt]
  LL --> aws[AWS eu-central-1<br/>Lambda, Step Functions, S3, Cognito, CloudFront]
  LL --> apple[App Store Server API]
  LL --> stripe[Stripe]
```

## 3. Components

The backend is one Python package, `letterlens`. Each module has one task.

| Module | Task |
|---|---|
| `api` | HTTP routes, request and response models, authentication, error format, security headers |
| `services` | Use cases: letters, questions, sharing, case inbox |
| `pipeline` | The steps classify, extract, verify, retrieve, explain, finalize, and the runners |
| `llm` | The gateway, the providers, versioned prompts, prices |
| `grounding` | German date and amount parsers, deadline rules, the verifier |
| `ml` | The letter-type classifier (dependency-free inference) |
| `rag` | The curated corpus and hybrid retrieval |
| `safety` | PII pseudonymization, the legal-advice guardrail, injection defence |
| `db` | Connection pool, row-level-security context, migrations, repositories |
| `crypto` | Envelope encryption (AES-256-GCM, per-user data keys) |
| `billing` | Stripe webhooks, App Store transaction verification |
| `handlers` | AWS Lambda entry points |

Dependencies point inwards: `api` → `services` → `pipeline` → `llm`, `grounding`, `rag`, `safety`.
The domain types in `domain.py` have no dependencies.

## 4. Request flow: a new letter

```mermaid
sequenceDiagram
  participant App as iOS / web
  participant API as API Lambda
  participant DB as PostgreSQL (RLS)
  participant SF as Step Functions
  participant W as Worker Lambda
  participant LLM as Model provider
  App->>App: scan + OCR on the device
  App->>API: POST /v1/letters (text lines, Idempotency-Key)
  API->>DB: rate limit, quota, insert encrypted state
  API->>SF: StartExecution(letter_id)
  API-->>App: 202 Accepted
  loop classify, extract, verify, retrieve, explain
    SF->>W: run step
    W->>DB: load and decrypt state
    W->>LLM: only for extract and explain (pseudonymized text)
    W->>DB: encrypt and save state
  end
  SF->>W: mark ready
  App->>API: GET /v1/letters/{id} (polling)
  API-->>App: facts, explanation, original lines
```

Each step is idempotent: it reads the state, computes, and writes the state.
Step Functions retries a failed step twice with backoff. If a step still fails,
the letter gets the status `failed`.

## 5. The pipeline

| Step | Method | Output |
|---|---|---|
| classify | TF-IDF + logistic regression + temperature scaling. Abstains below 0.5. | Letter type and calibrated probability |
| extract | Model with strict JSON schema and type-specific prompt; input is pseudonymized | Sender, dates, deadlines, amounts, references, each with line ids |
| verify | Deterministic parsers | Each fact `verified` or `needs_check`; relative deadlines estimated with the legal rules |
| retrieve | BM25 + optional embeddings, reciprocal rank fusion, type filter | Up to 4 dated passages with sources |
| explain | Model, in the reader's language, with citations | Summary sentences with line ids, next steps with passage ids |
| sanitize | Deterministic | Drops advice-like sentences, invented numbers, uncited steps, URLs |

If the model fails or a budget is spent, the pipeline does not stop. It uses the
rule-based extractor and a template explanation, and it marks the letter as
`degraded`. The client shows a warning.

## 6. Data model

| Table | Content | Isolation |
|---|---|---|
| `users` | Token subject, plan, preferred language. No e-mail address. | own row |
| `user_keys` | Wrapped data key per user | own row; read through an active share |
| `letters` | Status, type, encrypted pipeline state, expiry | owner; read through an active share |
| `shares` | Consent version, expiry, case status | owner; the receiving tenant |
| `messages` | Encrypted message and its translations | share participants |
| `tenants`, `memberships`, `tenant_invites` | Counselling services and employers | members |
| `llm_calls` | Cost ledger: tokens, list price, latency, prompt version. No text. | system and own rows |
| `audit_log` | Append-only actions | actor and tenant |
| `usage_counters`, `rate_limits`, `idempotency_keys`, `billing_events` | Operations | owner or system |

PostgreSQL row-level security enforces isolation. The application role does not
own the tables and cannot bypass RLS. 19 tests prove each rule
(`backend/tests/test_rls.py`).

## 7. Deployment view

| Concern | Service | Free-tier note |
|---|---|---|
| Edge, static web | CloudFront, S3 | 1 TB and 10 M requests per month always free |
| API | Lambda function URL behind CloudFront, with a secret origin header | 1 M requests per month always free |
| Pipeline | Step Functions Standard, Lambda worker | 4,000 state transitions per month always free (about 400 letters) |
| Identity | Cognito, Lite plan | free up to the MAU limit of the free tier |
| Database | Neon PostgreSQL 17, Frankfurt | free plan: 1 GB storage, 100 compute hours per month |
| Secrets | SSM Parameter Store SecureString | standard parameters are free |
| Observability | CloudWatch Logs (14 days), EMF metrics (9), alarms (6), X-Ray | inside the free limits |


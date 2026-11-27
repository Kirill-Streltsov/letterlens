# LetterLens

Scan an official German letter. Understand it in your language. Never miss the deadline.

LetterLens reads letters from the tax office, the Jobcenter, health insurers, the
immigration office and landlords. It explains each letter in plain language,
finds the deadlines and amounts, and checks every date against the original text.
It gives general information, not legal advice. For an individual case, it hands
the letter over to a free counselling service, with the reader's consent.

| Client | For | Main functions |
|---|---|---|
| iOS app (SwiftUI) | People who receive letters | Document scanner, on-device text recognition, summary in 6 languages, deadline cards with calendar and reminders, questions, sharing with a counsellor |
| Web app (Next.js) | Readers and counselling services | The same reader flow with in-browser text recognition; a case inbox, German summaries, reply translation and statistics for funding reports |

## Results

Measured on the golden set of 137 letters (synthetic letters with unseen seeds,
OCR-noise variants and 17 hand-written letters) and on 96 red-team questions in
6 languages. "Live" is the production model (Mistral, 27 November 2026, 532 calls,
0.12 USD); "rules" is the offline fallback that runs when the model is not available.
Reports: [live](backend/evals/reports/live.md), [offline](backend/evals/reports/offline.md).

| Metric | Live | Rules |
|---|---|---|
| Dates or amounts shown as "verified" that are not in the letter | **0** | **0** (also 0 of 91 injected hallucinations) |
| Explicit deadline recall / precision | 99.0 % / 100 % | 98.0 % / 94.1 % |
| Letters with every deadline exactly right | 99.3 % | 94.2 % |
| Letter date accuracy / amount recall | 99.3 % / 98.8 % | 99.3 % / 98.2 % |
| Amount direction (to pay / to receive) | 98.8 % | 93.4 % |
| Legal-advice requests caught / normal questions blocked | 100 % / 0 % | 85.2 % / 0 % |
| Prompt-injection attempts caught | 100 % | 100 % |
| Translation faithfulness (judge, per language) | 0.925 to 1.00; judge accuracy 95 % | – |
| Translations with one sentence per English sentence | 100 % | – |
| Key points in the summary (5 hand-written letters, 19 points) | 89.5 % to 94.7 % (three runs); judge false positives 0 % | – |
| Real and sample documents reviewed by a person | 31 (findings and fixes: [evaluation.md, section 8](docs/ai/evaluation.md)) | – |
| Retrieval recall@4 | 99.1 % | 99.1 % |
| Letter type on unseen layouts (leave-one-template-out) | 97.8 %, calibration error 0.32 → 0.01 | same model |

The test letters are synthetic and hand-written. Real, consented letters must be
added before these numbers describe real use; see [docs/ai/evaluation.md](docs/ai/evaluation.md).

## Architecture

```mermaid
flowchart LR
  subgraph Device
    iOS[iOS app<br/>VisionKit + Vision OCR]
    Web[Web app<br/>tesseract.js OCR]
  end
  iOS -- text lines only --> CF
  Web -- text lines only --> CF
  CF[CloudFront<br/>static web + /v1/*] --> API[Lambda: FastAPI<br/>auth, RLS context, quotas]
  API --> SFN[Step Functions<br/>classify → extract → verify → retrieve → explain]
  SFN --> W[Lambda: pipeline worker]
  W --> GW[LLM gateway<br/>budgets, retries, fallbacks, cost ledger]
  GW --> LLM[(Mistral EU<br/>or Claude / Bedrock)]
  API --> PG[(Neon PostgreSQL<br/>row-level security,<br/>per-user encryption)]
  W --> PG
  API --> COG[Cognito]
  API --> S3[(S3: optional images<br/>30-day expiry)]
```

The rule behind the design: **the model proposes, code verifies.** The model
extracts dates and amounts with a line reference. Deterministic code checks that
the cited line contains the value. Values that fail the check are shown as
"please check", never as facts. Details: [docs/architecture/overview.md](docs/architecture/overview.md).

## Repository

| Path | Content |
|---|---|
| [backend/](backend/) | Python 3.13: FastAPI API, pipeline, LLM gateway, grounding, classifier, RAG, safety, billing, tests, evaluation suite |
| [web/](web/) | Next.js static export, TypeScript, typed API client generated from the OpenAPI contract |
| [ios/](ios/) | SwiftUI app (XcodeGen) and the `LetterLensCore` Swift package |
| [infra/](infra/) | AWS CDK (Python) with cdk-nag, GitHub OIDC deploy role |
| [contracts/](contracts/) | OpenAPI document and response fixtures shared by all clients |
| [docs/](docs/) | Architecture, ADRs, AI evaluation, security, legal boundary, operations |

## Quick start (local, no accounts needed)

Prerequisites: Docker, [uv](https://docs.astral.sh/uv/), Node.js 22.

```bash
make seed   # PostgreSQL in Docker, migrations, demo data
make api    # API on http://localhost:8000 (offline model provider)
make web    # web app on http://localhost:3000
```

Sign in as `demo-client` (reader) or `counsellor-anna` (counselling service).
More: [docs/development.md](docs/development.md).

## Quality gates

```bash
make lint   # ruff, mypy --strict, eslint, tsc
make test   # 173 backend tests (with RLS isolation), infra assertions, web tests
make eval   # offline gate and fault-injection gate
cd ios/Packages/LetterLensCore && swift test   # Swift core and API contract tests
```

## Documentation

- [Deployment guide](docs/operations/deployment.md): the manual steps for AWS, Neon, Mistral, GitHub, Apple, Stripe
- [Architecture overview](docs/architecture/overview.md) and [decision records](docs/architecture/adr/)
- [AI pipeline](docs/ai/pipeline.md) and [evaluation](docs/ai/evaluation.md)
- [Threat model](docs/security/threat-model.md) and [data protection](docs/security/data-protection.md)
- [Legal-advice boundary (RDG)](docs/legal/rdg-boundary.md)
- [Runbook](docs/operations/runbook.md) and [cost model](docs/operations/cost.md)

## Status

The product is ready for a closed pilot after the checklist in the
[deployment guide](docs/operations/deployment.md#before-real-users-checklist).
The corpus and the legal boundary need a professional review before real users.

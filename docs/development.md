# Development

## Prerequisites

| Tool | Version | Install |
|---|---|---|
| Docker | any | Docker Desktop |
| uv | 0.5 or later | `pip install uv` or `brew install uv` |
| Node.js | 22 or later | `brew install node` |
| Xcode | 26 or later (iOS only) | App Store; then `brew install xcodegen` |

## Run locally

```bash
make seed    # PostgreSQL in Docker (port 5433), migrations, demo data
make api     # http://localhost:8000, API docs at /docs
make web     # http://localhost:3000
```

The local API uses the offline model provider and the dev authentication. Sign in
as `demo-client` or `counsellor-anna`.

To use a real model locally:

```bash
LETTERLENS_LLM_PROVIDER=mistral LETTERLENS_LLM_API_KEY=... make api
```

## Tests

| Command | Scope |
|---|---|
| `cd backend && uv run pytest` | unit, RLS isolation (needs Docker), API integration, gate test |
| `cd backend && uv run pytest -m "not db"` | without a database |
| `cd infra && uv run pytest` | CDK template assertions |
| `cd web && npm test` | library and component tests |
| `cd ios/Packages/LetterLensCore && swift test` | Swift core and contract tests |
| `ios/scripts/typecheck.sh` | iOS app against the simulator SDK, without a simulator |
| `make eval` | offline gate and fault-injection gate |

## Change the API

1. Change the models in `backend/src/letterlens/api/schemas.py` and the routes.
2. Run `make contract`. This updates `contracts/openapi.json` and the web types.
3. Run `cd backend && uv run python scripts/export_fixtures.py` (needs `make migrate`).
4. Update the Swift models in `ios/Packages/LetterLensCore/Sources/LetterLensCore/Models.swift` and run `swift test`.

## Change a prompt or the pipeline

1. Change the prompt and its version string in `llm/prompts.py`.
2. Run `make eval`. For prompt changes, also run the live profile (see [ai/evaluation.md](ai/evaluation.md)).
3. Add the report to the pull request.

## Retrain the classifier

```bash
cd backend && uv run python scripts/train_classifier.py
```

The script writes the model to `src/letterlens/ml/artifacts/letter_type.json` and
the metrics to `evals/reports/classifier.json`. Commit both.

## Database migrations

Add a file `backend/migrations/NNNN_description.sql`. Never edit an applied file.
Every new table needs `ENABLE ROW LEVEL SECURITY`, policies and a test in `tests/test_rls.py`.

## Code style

- Python: ruff (lint and format), mypy `--strict`. Line length 110.
- TypeScript: eslint, `tsc --noEmit`, strict mode.
- Commit messages: imperative mood, one subject line.

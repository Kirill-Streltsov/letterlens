# Local development shortcuts. Requires: uv, node 22+, docker.
DB_ADMIN = postgresql://letterlens_owner:letterlens_owner@localhost:5433/letterlens
export LETTERLENS_DATABASE_URL = postgresql://letterlens_app:letterlens_app@localhost:5433/letterlens

.PHONY: db migrate seed api web test eval lint contract build-lambda synth

db:            ## start PostgreSQL
	docker compose up -d --wait
migrate: db    ## apply SQL migrations as the owner role
	cd backend && LETTERLENS_DATABASE_ADMIN_URL=$(DB_ADMIN) LETTERLENS_DB_APP_PASSWORD=letterlens_app uv run python -m letterlens.db.migrate
seed: migrate  ## demo tenant, counsellor and letters
	cd backend && PYTHONPATH=. uv run python scripts/seed_demo.py
api:           ## API on :8000 (offline LLM provider unless LETTERLENS_LLM_PROVIDER is set)
	cd backend && uv run uvicorn letterlens.api.app:create_app --factory --port 8000 --reload
web:           ## web app on :3000
	cd web && npm run dev
test:          ## all tests
	cd backend && uv run pytest -q
	cd infra && uv run pytest -q
	cd web && npm test
eval:          ## offline and fault-injection gates
	cd backend && uv run python -m evals.run --profile offline && uv run python -m evals.run --profile chaos
lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy src
	cd web && npm run lint && npm run typecheck
contract:      ## regenerate the OpenAPI contract and the typed web client
	cd backend && uv run python scripts/export_openapi.py
	cd web && npm run gen:api
build-lambda:
	infra/scripts/build_lambda.sh
synth: build-lambda
	cd infra && CDK_DISABLE_VERSION_CHECK=1 npx --yes aws-cdk@2 synth -c stage=prod --quiet

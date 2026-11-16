# ADR-0008: Hand-written clients guarded by contract fixtures

Status: accepted · Date: 2026-11-16

## Context

Three clients use the API: the web app, the iOS app and tests. The OpenAPI
document is generated from the FastAPI models. Generated Swift code from
OpenAPI 3.1 with nullable unions (`anyOf: [T, null]`) is hard to use in SwiftUI.

## Decision

1. Export the OpenAPI document to `contracts/openapi.json`.
2. The web app generates its TypeScript types from it (`npm run gen:api`).
3. The iOS app uses hand-written `Codable` models in the `LetterLensCore` package.
4. `backend/scripts/export_fixtures.py` writes real API responses to `contracts/fixtures/`.
   The Swift tests decode every fixture. A backend test validates every fixture against the current response models.

## Consequences

- A breaking API change fails a test on the server side or on the client side.
- The Swift models stay idiomatic.
- After an API change, run `make contract` and `scripts/export_fixtures.py`, then run the Swift tests.

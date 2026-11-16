# ADR-0004: Neon PostgreSQL with RLS; in-memory hybrid retrieval

Status: accepted · Date: 2026-11-16

## Context

Readers own letters. Counselling services see only letters that a reader shared
with them, and only while the consent is active. A bug in one query must not leak
data. The explanation corpus is small (24 passages) and curated by hand.

## Decision

1. Store all data in PostgreSQL with row-level security (RLS). The API sets the
   user, the tenants and the system flag per transaction with `set_config(..., true)`.
   The application role does not own the tables and has no BYPASSRLS.
2. Shares carry the consent version and an expiry. RLS checks "active share" in every policy that gives tenant access.
3. Use Neon (free plan, Frankfurt). Disable server-side prepared statements, because Neon's pooler runs in transaction mode.
4. Keep the corpus in Markdown files in the repository. Build a BM25 index at cold start.
   Fuse it with embedding similarity when an embedding index exists (reciprocal rank fusion).
   Filter passages by letter type.

## Consequences

- Isolation is tested as the real application role (`tests/test_rls.py`, 19 tests).
- A counsellor can read the owner's wrapped data key only through an active share; without the KEK, the wrapped key is useless.
- Retrieval needs no database round trip and no vector extension. At 24 passages, BM25 + type filter reaches recall@4 of 99 %.
- Corpus changes go through code review, which is the right control for content with legal weight.

## When to change

Move the corpus to pgvector when it exceeds about 2,000 passages or when tenants
add their own documents. The `HybridRetriever` interface stays the same.

# ADR-0003: Provider-neutral LLM gateway, Mistral by default

Status: accepted · Date: 2026-11-16

## Context

The product needs a multilingual model with structured output. The budget is 0 EUR.
Letters are sensitive, so the model provider should process data in the EU and
must not train on it. Provider prices, limits and quality change often.

## Decision

1. All model calls go through one module, `letterlens.llm.gateway`. Application code never calls a provider SDK.
2. The gateway does: model routing per task, a fallback chain, retries with backoff for transient errors, a strict JSON schema with one repair attempt, a monthly spend budget and a daily token budget per user, and a cost ledger row per call.
3. Providers:
   - `mistral` / `openai_compat` (default): Mistral free tier, EU. One adapter also covers Groq, Ollama and vLLM.
   - `anthropic` / `bedrock` (paid production profile): Claude through the Anthropic SDK, on the Claude API or on Amazon Bedrock. Server-side refusal fallbacks are on for the Claude API.
   - `fake`: deterministic and offline, for development, tests and CI.
4. Production refuses to start with Mistral unless the operator confirms the training opt-out (`llm_training_opt_out_confirmed`).

## Consequences

- A model change is a configuration change plus a live evaluation run.
- Free tiers have rate limits. The gateway retries and then degrades to rules; the user sees a warning, not an error.
- The ledger records the list price also on free tiers, so the cost of a paid plan is known before the switch.

## Alternatives

- **Amazon Bedrock only** (reference plan): not free. Kept as an option.
- **Gemini free tier**: the free tier may use content to improve products. Rejected for sensitive letters.
- **Self-hosted model**: no free GPU hosting. Rejected.

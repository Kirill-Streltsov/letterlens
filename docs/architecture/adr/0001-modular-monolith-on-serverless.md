# ADR-0001: Modular monolith on Lambda and Step Functions

Status: accepted · Date: 2026-11-13

## Context

One engineer builds and operates LetterLens. Traffic is low and comes in bursts
(letters arrive in the morning post). The pipeline has slow steps (model calls of
5 to 20 seconds) and must survive a failure in one step.

## Decision

1. Write the backend as one Python package with clear modules (see the overview).
2. Run the API as one Lambda function behind a function URL. FastAPI runs through Mangum.
3. Run the pipeline as a Step Functions Standard workflow. Each task calls one
   worker Lambda function with the step name. The same step functions run
   in-process for local development and tests (`InProcessRunner`).

## Consequences

- One deploy, one database, one set of tests. No network calls between services.
- Each pipeline step has its own retry policy and its own entry in the execution history.
- Lambda cold starts add about 1 second to the first request. The client polls, so users do not wait on a held connection.
- The pipeline state is stored (encrypted) between steps. Steps must be idempotent. They are.

## Alternatives

- **ECS Fargate + ALB** (the original platform plan): no cold starts, but about 20 to 40 EUR per month minimum. Rejected for the budget.
- **SQS + one worker per letter**: cheaper per letter, but no per-step retries and no execution history. Rejected.
- **Microservices**: no team-scaling reason exists. Rejected.

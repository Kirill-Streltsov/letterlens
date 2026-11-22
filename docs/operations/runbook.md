# Runbook

Each alarm sends an e-mail to the address in `infra/cdk.json` (`alarmEmail`).
For each alarm, do the steps in sequence. Stop when the cause is found.

## Logs

All functions write JSON lines. Open **CloudWatch > Logs Insights**, select the
log groups `LetterLens-prod-*Logs*`, and use these queries.

Errors in the last hour:

```
fields @timestamp, level, msg, logger, request_id, exc_type
| filter level = "ERROR"
| sort @timestamp desc | limit 50
```

Pipeline steps of one letter:

```
fields @timestamp, step, ms, degraded, msg
| filter letter_id = "<letter-id>"
| sort @timestamp asc
```

Slow API routes:

```
fields route, ms
| filter msg = "request"
| stats pct(ms, 95) as p95, count() as n by route
| sort p95 desc
```

Model failures by type:

```
fields model, error
| filter msg = "llm call failed"
| stats count() by model, error
```

Log lines contain no letter text. Do not add any.

## Alarms

### ApiErrors (5 or more errors in 5 minutes)

1. Run the "Errors in the last hour" query.
2. If `exc_type` is `OperationalError` or `PoolTimeout`: check Neon status and the Neon compute hours (free plan: 100 per month). A suspended or over-quota compute causes this.
3. If the errors started after a deploy: run the Deploy workflow on the previous commit (rollback).

### ApiLatencyP95 (p95 over 10 seconds, 15 minutes)

1. Run the "Slow API routes" query.
2. `/v1/letters/{letter_id}/questions` is slow when the model is slow. Check the "Model failures" query for timeouts and rate limits.
3. Cold starts after a quiet period are normal. They are not an incident.

### WorkerErrors or PipelineFailures

1. Open **Step Functions > Pipeline > Executions**, filter by status Failed, and open one execution.
2. The failed state shows the step and the error.
3. `LookupError`: the letter was deleted while it was processing. No action.
4. Model errors: the gateway already retried and fell back. Check the provider status and the API key in SSM.
5. Letters in status `failed` can be submitted again by the reader. No data is lost.

### LlmSpendDaily

The daily list price of model calls is over the limit.

1. Call `GET /v1/admin/costs?days=2` as platform admin. Find the task and model with the highest cost.
2. Check for abuse: many letters from one user (`usage_counters`) or many questions (`rate_limits`).
3. To stop spend at once, lower `LETTERLENS_MONTHLY_LLM_BUDGET_USD` in `infra/cdk.json` and deploy, or set `llm_api_key` in SSM to an empty value. The pipeline then runs in degraded mode (rules only).

### GuardrailSpike (50 or more refusals in one hour)


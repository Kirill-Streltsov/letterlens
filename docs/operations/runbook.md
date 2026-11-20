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


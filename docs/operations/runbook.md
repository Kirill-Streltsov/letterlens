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


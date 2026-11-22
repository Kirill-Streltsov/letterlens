# Threat model

Method: STRIDE per trust boundary. Each threat has a mitigation and, where possible,
an automated test. Review this document when an interface or a processor changes.

## 1. Assets

| Asset | Sensitivity |
|---|---|
| Letter text and results | Very high: tax, health, residence, debts |
| Messages between reader and counsellor | Very high |
| Data keys (KEK in SSM, wrapped DEKs in the database) | Critical: they protect all of the above |
| Account data (token subject, plan, display name) | Medium |
| Cost ledger and audit log | Low (no content) |

## 2. Trust boundaries

1. Device → CloudFront → API (internet)
2. API / worker → Neon PostgreSQL (internet, TLS)
3. Worker → model provider (internet, TLS)
4. Reader ↔ counsellor (through shares)
5. Letter content → model (untrusted text inside the prompt)

## 3. Threats


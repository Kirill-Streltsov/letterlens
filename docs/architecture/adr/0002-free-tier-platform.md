# ADR-0002: Free-tier platform and its trade-offs

Status: accepted · Date: 2026-11-16

## Context

The platform must cost 0 EUR per month at pilot volume. The reference platform
(Fargate, Aurora Serverless v2, WAF, KMS customer keys, Secrets Manager, NAT
gateway) costs a few hundred euros per month before model usage.

## Decision

| Reference choice | Free choice | What we give up |
|---|---|---|
| Fargate + ALB | Lambda function URL behind CloudFront | Long-lived connections; cold starts |
| API Gateway | Function URL + secret origin header set by CloudFront | Usage plans, request validation at the edge |
| Aurora Serverless v2 | Neon PostgreSQL free plan (Frankfurt) | AWS-native backups and IAM auth; 1 GB storage |
| AWS WAF | Rate limits and quotas in the API (PostgreSQL counters) | Edge filtering of bad traffic |
| KMS customer-managed keys per tenant | Application envelope encryption, KEK in SSM SecureString | Hardware-backed key, key-use audit in CloudTrail |
| Secrets Manager | SSM Parameter Store standard parameters | Automatic rotation |
| CloudWatch custom dashboards | Cost ledger table + `/v1/admin/costs`, 9 EMF metrics | Dashboards |
| NAT gateway, VPC | Lambda outside a VPC | Private networking to the database (TLS is used) |

Every paid feature has an upgrade path that does not change the application code
(environment settings or one CDK construct).

## Consequences

- The monthly cost is 0 EUR until the free limits (see [cost.md](../../operations/cost.md)).
- Neon is a sub-processor outside AWS. Data stays in Frankfurt. The privacy policy names it.
- Without WAF, a large attack can use the free Lambda and CloudFront quotas. The API rejects unauthenticated requests early, and the budget alarm reports the cost.
- cdk-nag findings for these choices are suppressed with the reasons in `infra/app.py`.

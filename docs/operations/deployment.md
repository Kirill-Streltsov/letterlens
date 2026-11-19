# Deployment guide

This guide puts LetterLens into production. Do the steps in sequence. Each step
names the person who does it and the result that you must see.

Time: approximately 90 minutes. Cost: 0 EUR per month at pilot volume (see
[cost.md](cost.md)). The Apple Developer Program (99 USD per year) is
necessary only for TestFlight and the App Store.

## Overview

| Step | Where | Result |
|---|---|---|
| 1 | GitHub | The repository accepts workflow files |
| 2 | Neon | A PostgreSQL database in Frankfurt |
| 3 | Mistral | An API key with training opt-out |
| 4 | AWS | An account, a budget alarm, a bootstrapped CDK environment |
| 5 | AWS | The GitHub deploy role (OIDC) |
| 6 | AWS SSM | The runtime secrets |
| 7 | GitHub | The deploy secrets and the `production` environment |
| 8 | GitHub Actions | The first deployment |
| 9 | Terminal | The first counselling service and its admin |
| 10 | GitHub Actions | The live evaluation and the language status |
| 11 | Xcode, App Store Connect | The iOS app in TestFlight |
| 12 | Stripe (optional) | Web subscriptions and counsellor seats |

## 1. GitHub: allow workflow files

The GitHub CLI token on this Mac cannot push files in `.github/workflows/`.

1. Run this command and approve the scope in the browser:
   ```bash
   gh auth refresh -h github.com -s workflow
   ```
2. Push the local commits:
   ```bash
   cd ~/letterlens && git push
   ```

Result: the CI workflow starts on GitHub and the jobs `backend`, `eval-gate`,
`infra` and `web` pass.

## 2. Neon: create the database

1. Create a free account at <https://neon.com>.
2. Create a project. Name: `letterlens`. Region: **AWS Europe Central 1 (Frankfurt)**. PostgreSQL version: 17.
3. Copy the connection string of the owner role (for example `neondb_owner`). Use the **direct** host (no `-pooler` in the host name). This is `NEON_ADMIN_URL`. Keep `?sslmode=require` at the end.
4. Make a password for the application role:
   ```bash
   openssl rand -base64 24 | tr -d '/+=' | cut -c1-28
   ```
   This is `NEON_APP_PASSWORD`.
5. Apply the migrations from your Mac. This also creates the role `letterlens_app`:
   ```bash
   cd ~/letterlens/backend
   LETTERLENS_DATABASE_ADMIN_URL='<NEON_ADMIN_URL>' LETTERLENS_DB_APP_PASSWORD='<NEON_APP_PASSWORD>' \
     uv run python -m letterlens.db.migrate
   ```
6. Make the application URL. Use the **pooled** host (with `-pooler`), the user `letterlens_app` and the password from step 4:
   `postgresql://letterlens_app:<NEON_APP_PASSWORD>@<endpoint>-pooler.<region>.aws.neon.tech/neondb?sslmode=require`.
   This is `DATABASE_URL`.

Result: `applied: ['0001_init']`.

## 3. Mistral: create the API key

The default model provider is Mistral (EU company, EU processing, free tier).
See [ADR-0003](../architecture/adr/0003-llm-gateway-and-providers.md).

1. Create an account at <https://console.mistral.ai>. Select the free plan.
2. Open **Admin console > Privacy**. Turn **off** the use of your API data for training.
3. Create an API key. This is `MISTRAL_API_KEY`.

Result: you have a key, and training on your data is off.

> The production settings refuse to start with Mistral until you confirm step 2
> (parameter `llm_training_opt_out_confirmed` in step 6).

## 4. AWS: account, budget, CDK bootstrap

1. Create an AWS account at <https://aws.amazon.com>. Select region **Europe (Frankfurt) eu-central-1** for all work.
2. Turn on MFA for the root user. Do not use the root user after this step.
3. In IAM Identity Center, create a user with the `AdministratorAccess` permission set. Use this user for steps 4 to 6 only.
4. Install the AWS CLI and sign in:
   ```bash
   brew install awscli
   aws configure sso
   ```
5. Set your e-mail address for alarms and the budget in `infra/cdk.json`, key `stages.prod.alarmEmail`.
6. If the Cognito domain prefix `letterlens-ks26` is not available, change `stages.prod.cognitoDomainPrefix` in `infra/cdk.json`.
7. Bootstrap CDK in the account:
   ```bash
   cd ~/letterlens/infra
   npx aws-cdk@2 bootstrap aws://<ACCOUNT_ID>/eu-central-1
   ```

Result: the stack `CDKToolkit` exists in CloudFormation.


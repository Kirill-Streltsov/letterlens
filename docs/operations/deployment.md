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

## 5. AWS: the GitHub deploy role

The deploy role lets GitHub Actions deploy without stored AWS keys (OIDC).

```bash
cd ~/letterlens/infra
make -C .. build-lambda
npx aws-cdk@2 deploy LetterLens-ci -c stage=prod
```

Result: the output `DeployRoleArn`. This is `AWS_DEPLOY_ROLE_ARN`.

## 6. AWS SSM: the runtime secrets

The Lambda functions read these parameters at cold start. Standard parameters
are free. Replace the values in angle brackets.

```bash
P=/letterlens/prod
aws ssm put-parameter --name $P/database_url --type SecureString --value '<DATABASE_URL>'
aws ssm put-parameter --name $P/kek_base64 --type SecureString --value "$(openssl rand -base64 32)"
aws ssm put-parameter --name $P/llm_api_key --type SecureString --value '<MISTRAL_API_KEY>'
aws ssm put-parameter --name $P/llm_training_opt_out_confirmed --type String --value true
```

> **Warning:** the parameter `kek_base64` encrypts all letters. If you lose it,
> you cannot read the stored letters. Do not change it after the first letter.
> To keep a copy, print it once and store it in your password manager.

Result: `aws ssm get-parameters-by-path --path /letterlens/prod/` shows four parameters.

## 7. GitHub: secrets and environment

1. Make the origin secret:
   ```bash
   openssl rand -hex 32
   ```
2. In the repository settings, create the environment **production**.
3. In this environment, add these secrets:

| Secret | Value |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | output of step 5 |
| `NEON_ADMIN_URL` | step 2.3 |
| `NEON_APP_PASSWORD` | step 2.4 |
| `ORIGIN_VERIFY_SECRET` | step 7.1 |

4. Add `MISTRAL_API_KEY` as a **repository** secret (the live evaluation uses it).
5. Add the **repository variable** `DEPLOY_ENABLED` with the value `true`. Without it,
   pushes to `main` do not deploy; only a manual run of the Deploy workflow does.

## 8. First deployment

1. Open **Actions > Deploy > Run workflow** on the branch `main`.
2. Wait for the job to finish (approximately 10 minutes).
3. Open the job log. Find the line `SiteUrl`.

Result: the smoke test passes. `https://<SiteUrl>/health` returns `{"status":"ok"}`.
Later pushes to `main` deploy automatically after CI passes.

To see all stack outputs:

```bash
aws cloudformation describe-stacks --stack-name LetterLens-prod --query 'Stacks[0].Outputs'
```

## 9. First counselling service and admin

1. Create the counselling service. The command prints its id:
   ```bash
   cd ~/letterlens/backend
   LETTERLENS_SSM_PREFIX=/letterlens/prod/ uv run python -m letterlens.admin \
     create-tenant "Migrationsberatung Musterstadt" --city Bochum --languages de,tr,ar,uk
   ```
2. Create an admin invite code for this service:
   ```bash
   LETTERLENS_SSM_PREFIX=/letterlens/prod/ uv run python -m letterlens.admin invite <tenant-id> --role admin
   ```
3. Give the code to the counsellor. The counsellor signs up on the web app, opens **Settings**, and enters the code.
4. To give yourself the cost dashboard, add your user to the Cognito group `platform_admin`:
   ```bash
   aws cognito-idp admin-add-user-to-group --user-pool-id <UserPoolId> --username <your-email> --group-name platform_admin
   ```

Result: the counsellor sees **Case inbox** in the navigation.

## 10. Live evaluation and language status

The offline gate runs on every pull request. Run the live gate with the real model
before you invite users, and after every prompt or model change.

1. Open **Actions > CI > Run workflow**. Select **live_eval**.
2. Read the job summary. All gates must pass.
3. Update the language status on your Mac and commit the change:
   ```bash
   cd ~/letterlens/backend
   LETTERLENS_LLM_PROVIDER=mistral LETTERLENS_LLM_API_KEY='<MISTRAL_API_KEY>' \
     uv run python -m evals.run --profile live --update-languages
   git commit -am "Language status from live evaluation" && git push
   ```

Result: `languages.yaml` marks each language `enabled` or `experimental`.

## 11. iOS app in TestFlight

1. In the Apple Developer portal, create the App ID `app.letterlens.ios`.
2. In App Store Connect, create the app and the auto-renewable subscription `app.letterlens.plus.monthly` (group "LetterLens Plus", 4.99 EUR).
3. In App Store Connect, set **App Store Server Notifications V2** to `https://<SiteUrl>/v1/billing/appstore/notifications`.
4. Put the stack outputs into `ios/Config/Release.xcconfig`: the site domain, `AuthDomain` and `IosClientId`.
5. Generate the project and open it:
   ```bash
   cd ~/letterlens/ios && xcodegen generate && open LetterLens.xcodeproj
   ```
6. Select your team in **Signing & Capabilities**. Add the capability **In-App Purchase**.
7. Select **Product > Archive**, then **Distribute App > TestFlight**.

To run the app against your local API, use the Debug configuration. It uses
`http://localhost:8000` and the demo user. Start the API with `make api`.

## 12. Stripe (optional)

Stripe sells Plus on the web and counsellor seats to services.

1. Create a Stripe account. Stay in **test mode** until the legal review is complete.
2. Create two recurring prices: Plus (4.99 EUR per month) and Seat (29 EUR per month per seat).
3. Create a webhook endpoint `https://<SiteUrl>/v1/billing/stripe/webhook` for the events `customer.subscription.created`, `customer.subscription.updated` and `customer.subscription.deleted`.
4. Store the values:
   ```bash
   P=/letterlens/prod
   aws ssm put-parameter --name $P/stripe_secret_key --type SecureString --value '<sk_test_...>'
   aws ssm put-parameter --name $P/stripe_webhook_secret --type SecureString --value '<whsec_...>'
   aws ssm put-parameter --name $P/stripe_price_plus --type String --value '<price_...>'
   aws ssm put-parameter --name $P/stripe_price_seat --type String --value '<price_...>'
   ```
5. Force a cold start of the API so that it reads the new values:
   ```bash
   aws lambda update-function-configuration --function-name <ApiFunctionName> \
     --description "reload $(date +%s)"
   ```

## Before real users: checklist

- [ ] A lawyer has reviewed the legal-advice boundary ([rdg-boundary.md](../legal/rdg-boundary.md)).
- [ ] A counsellor has reviewed every corpus entry and set `reviewed_by` in `backend/corpus/*.md`.
- [ ] The privacy policy names all processors ([data-protection.md](../security/data-protection.md)).
- [ ] The live evaluation passes, and you have added real, consented letters to the golden set.
- [ ] Counsellor accounts use MFA (Cognito, TOTP).
- [ ] A custom domain with its own certificate replaces the CloudFront domain.

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


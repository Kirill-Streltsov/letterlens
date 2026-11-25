#!/usr/bin/env python3
"""CDK entry point.

npx cdk synth -c stage=prod
npx cdk deploy LetterLens-prod -c stage=prod
npx cdk deploy LetterLens-ci            # once, with an admin profile
"""

from __future__ import annotations

import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks, NagPackSuppression, NagSuppressions

from letterlens_infra.ci import LetterLensCiStack
from letterlens_infra.stack import LetterLensStack

app = cdk.App()
stage = app.node.try_get_context("stage") or "dev"
config = dict(app.node.try_get_context("stages")[stage])
# The origin secret comes from the environment (GitHub secret), never from git.
config["originVerifySecret"] = os.environ.get("LETTERLENS_ORIGIN_VERIFY_SECRET", "local-synth-only")
# The alarm address is personal data: it comes from the environment (GitHub secret ALARM_EMAIL), not from git.
config["alarmEmail"] = os.environ.get("LETTERLENS_ALARM_EMAIL", config.get("alarmEmail", ""))
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=config.get("region", os.environ.get("CDK_DEFAULT_REGION", "eu-central-1")),
)

stack = LetterLensStack(app, f"LetterLens-{stage}", stage=stage, config=config, env=env)
ci = LetterLensCiStack(app, "LetterLens-ci", repository=app.node.try_get_context("repository"), env=env)

for s in (stack, ci):
    cdk.Tags.of(s).add("project", "letterlens")
    cdk.Tags.of(s).add("stage", stage)

cdk.Aspects.of(app).add(AwsSolutionsChecks(verbose=True))

# Each suppression is a decision with a reason (docs/architecture/adr).
NagSuppressions.add_stack_suppressions(
    stack,
    [
        NagPackSuppression(
            id="AwsSolutions-IAM4",
            reason="AWSLambdaBasicExecutionRole is the minimal managed policy for logs.",
        ),
        NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="Wildcards are scoped to one bucket's objects, one SSM path, X-Ray, or Bedrock models (ADR-0002).",
        ),
        NagPackSuppression(
            id="AwsSolutions-S1",
            reason="Server access logs cost storage; CloudTrail data events are the paid upgrade path.",
        ),
        NagPackSuppression(
            id="AwsSolutions-S10",
            reason="enforce_ssl is set; the remaining finding is for the CDK auto-delete helper.",
        ),
        NagPackSuppression(
            id="AwsSolutions-COG1",
            reason="NIST SP 800-63B: minimum length 10 plus digits; no symbol or case rules, which hurt users with non-Latin keyboards.",
        ),
        NagPackSuppression(
            id="AwsSolutions-COG2",
            reason="MFA is optional (TOTP) for clients; counsellor accounts are asked to enable it (runbook).",
        ),
        NagPackSuppression(
            id="AwsSolutions-COG3",
            reason="Cognito threat protection needs the Plus plan (paid); rate limits run in the API.",
        ),
        NagPackSuppression(
            id="AwsSolutions-COG8", reason="Lite plan keeps Cognito inside the free tier (ADR-0002)."
        ),
        NagPackSuppression(
            id="AwsSolutions-CFR1", reason="No geo restriction: users travel; data stays in the EU at rest."
        ),
        NagPackSuppression(
            id="AwsSolutions-CFR2",
            reason="AWS WAF is paid; the API enforces rate limits and auth (ADR-0002, threat model T7).",
        ),
        NagPackSuppression(
            id="AwsSolutions-CFR3",
            reason="CloudFront access logs cost storage; Lambda logs record every API request.",
        ),
        NagPackSuppression(
            id="AwsSolutions-CFR4",
            reason="Default CloudFront certificate; a custom domain with TLSv1.2_2021 is a launch task.",
        ),
        NagPackSuppression(
            id="AwsSolutions-L1",
            reason="Python 3.13 is the newest runtime supported by every dependency wheel.",
        ),
        NagPackSuppression(
            id="AwsSolutions-SF1",
            reason="Pipeline logs ERROR level only, to stay in the free log volume; X-Ray tracing is on.",
        ),
        NagPackSuppression(id="AwsSolutions-SNS3", reason="enforce_ssl is set on the topic."),
    ],
)
NagSuppressions.add_stack_suppressions(
    ci,
    [
        NagPackSuppression(
            id="AwsSolutions-IAM5",
            reason="The deploy role may only assume the CDK bootstrap roles of this account.",
        ),
    ],
)

app.synth()

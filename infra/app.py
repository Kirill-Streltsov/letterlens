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

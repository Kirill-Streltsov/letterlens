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


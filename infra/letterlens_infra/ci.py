"""GitHub Actions deploy role (OIDC). Deploy once by hand; CI then needs no AWS keys.

The role can only assume the CDK bootstrap roles, so its permissions are the
same as `cdk deploy` and nothing more. Only the main branch of one repository,
running in the GitHub environment "production", can assume it.
"""

from __future__ import annotations

from typing import Any

from aws_cdk import Aws, CfnOutput, Duration, Stack
from aws_cdk import aws_iam as iam
from constructs import Construct


class LetterLensCiStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, *, repository: str, **kwargs: Any) -> None:
        super().__init__(scope, construct_id, **kwargs)
        provider = iam.OpenIdConnectProvider(
            self,
            "GitHub",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )
        role = iam.Role(
            self,
            "DeployRole",

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
            role_name="letterlens-github-deploy",
            max_session_duration=Duration.hours(1),
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"},
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": f"repo:{repository}:environment:production"
                    },
                },
            ),
        )
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[
                    f"arn:aws:iam::{Aws.ACCOUNT_ID}:role/cdk-hnb659fds-*-{Aws.ACCOUNT_ID}-{Aws.REGION}"
                ],
            )
        )
        # Read-only access for the post-deploy smoke test and migrations config.
        role.add_to_policy(
            iam.PolicyStatement(
                actions=["cloudformation:DescribeStacks"],
                resources=[f"arn:aws:cloudformation:{Aws.REGION}:{Aws.ACCOUNT_ID}:stack/LetterLens-*/*"],
            )
        )
        CfnOutput(self, "DeployRoleArn", value=role.role_arn)

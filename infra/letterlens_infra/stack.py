"""LetterLens on AWS, sized for the always-free tier (ADR-0002).

Request path:  client -> CloudFront -> (static web: S3) | (/v1/*: Lambda function URL -> FastAPI)
Async path:    API -> Step Functions (Standard) -> worker Lambda, one invocation per pipeline step
Data:          Neon PostgreSQL (outside AWS, EU region) with RLS; S3 for optional letter images
Secrets:       SSM Parameter Store SecureString (free), loaded at cold start
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from aws_cdk import (
    Aws,
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
)
from aws_cdk import aws_budgets as budgets
from aws_cdk import aws_cloudfront as cloudfront
from aws_cdk import aws_cloudfront_origins as origins
from aws_cdk import aws_cloudwatch as cw
from aws_cdk import aws_cloudwatch_actions as cw_actions
from aws_cdk import aws_cognito as cognito
from aws_cdk import aws_events as events
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_iam as iam
from aws_cdk import aws_lambda as lambda_
from aws_cdk import aws_logs as logs
from aws_cdk import aws_s3 as s3
from aws_cdk import aws_s3_deployment as s3deploy
from aws_cdk import aws_sns as sns
from aws_cdk import aws_sns_subscriptions as subs
from aws_cdk import aws_ssm as ssm
from aws_cdk import aws_stepfunctions as sfn
from aws_cdk import aws_stepfunctions_tasks as tasks
from constructs import Construct

ROOT = Path(__file__).resolve().parents[2]
LAMBDA_DIR = ROOT / "infra" / "build" / "lambda"
WEB_DIR = ROOT / "web" / "out"
PIPELINE_STEPS = ("classify", "extract", "verify", "retrieve")


class LetterLensStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, *, stage: str, config: dict[str, Any], **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        prod = stage == "prod"
        removal = RemovalPolicy.RETAIN if prod else RemovalPolicy.DESTROY
        ssm_prefix = f"/letterlens/{stage}/"
        origin_secret: str = config["originVerifySecret"]

        # ------------------------------------------------------------------
        # Storage
        # ------------------------------------------------------------------
        # A deterministic name lets functions and policies refer to the bucket without a
        # CloudFormation reference; that breaks the cycle bucket CORS -> CloudFront -> API -> bucket.
        letters_bucket_name = f"letterlens-{stage}-letters-{Aws.ACCOUNT_ID}-{Aws.REGION}"
        letters_bucket_arn = f"arn:aws:s3:::{letters_bucket_name}"
        letters_bucket = s3.Bucket(
            self,
            "LettersBucket",
            bucket_name=letters_bucket_name,
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=removal,
            auto_delete_objects=not prod,
            lifecycle_rules=[
                # Images are deleted together with their letter; this rule is the backstop.
                s3.LifecycleRule(
                    prefix="letters/", expiration=Duration.days(config["retentionBackstopDays"])
                ),
                s3.LifecycleRule(abort_incomplete_multipart_upload_after=Duration.days(1)),
            ],
        )
        web_bucket = s3.Bucket(
            self,
            "WebBucket",
            encryption=s3.BucketEncryption.S3_MANAGED,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
        )

        # ------------------------------------------------------------------
        # Identity
        # ------------------------------------------------------------------
        user_pool = cognito.UserPool(
            self,
            "Users",
            user_pool_name=f"letterlens-{stage}",
            feature_plan=cognito.FeaturePlan.LITE,
            self_sign_up_enabled=True,
            sign_in_aliases=cognito.SignInAliases(email=True),
            auto_verify=cognito.AutoVerifiedAttrs(email=True),
            # NIST SP 800-63B: length, not composition rules (see cdk-nag COG1 suppression).
            password_policy=cognito.PasswordPolicy(
                min_length=10, require_symbols=False, require_uppercase=False, require_digits=True
            ),
            mfa=cognito.Mfa.OPTIONAL,
            mfa_second_factor=cognito.MfaSecondFactor(otp=True, sms=False),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            deletion_protection=prod,
            removal_policy=removal,
        )
        domain = user_pool.add_domain(
            "Domain", cognito_domain=cognito.CognitoDomainOptions(domain_prefix=config["cognitoDomainPrefix"])
        )
        for group in ("counsellor", "platform_admin"):
            cognito.CfnUserPoolGroup(
                self, f"Group{group}", user_pool_id=user_pool.user_pool_id, group_name=group
            )

        # ------------------------------------------------------------------
        # Compute
        # ------------------------------------------------------------------
        common_env = {
            "LETTERLENS_ENV": "prod" if prod else "dev",
            "LETTERLENS_AUTH_MODE": "cognito",
            "LETTERLENS_COGNITO_REGION": Aws.REGION,
            "LETTERLENS_COGNITO_USER_POOL_ID": user_pool.user_pool_id,
            "LETTERLENS_LETTERS_BUCKET": letters_bucket_name,
            "LETTERLENS_AWS_REGION": Aws.REGION,
            "LETTERLENS_SSM_PREFIX": ssm_prefix,
            "LETTERLENS_LLM_PROVIDER": config["llmProvider"],
            "LETTERLENS_LLM_MODEL_EXTRACT": config["llmModelExtract"],
            "LETTERLENS_LLM_MODEL_EXPLAIN": config["llmModelExplain"],
            "LETTERLENS_LLM_MODEL_GUARD": config["llmModelGuard"],
            "LETTERLENS_MONTHLY_LLM_BUDGET_USD": str(config["monthlyLlmBudgetUsd"]),
            "LETTERLENS_DEFAULT_RETENTION_DAYS": "30",
            "POWERTOOLS_SERVICE_NAME": "letterlens",
        }
        code = lambda_.Code.from_asset(str(LAMBDA_DIR))


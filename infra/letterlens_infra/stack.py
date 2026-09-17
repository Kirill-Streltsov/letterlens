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



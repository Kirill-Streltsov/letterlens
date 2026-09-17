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

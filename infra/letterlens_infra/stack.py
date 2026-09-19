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

        def function(
            name: str, handler: str, memory: int, timeout: Duration, env: dict[str, str]
        ) -> lambda_.Function:
            log_group = logs.LogGroup(
                self,
                f"{name}Logs",
                retention=logs.RetentionDays.TWO_WEEKS,
                removal_policy=RemovalPolicy.DESTROY,
            )
            fn = lambda_.Function(
                self,
                name,
                runtime=lambda_.Runtime.PYTHON_3_13,
                architecture=lambda_.Architecture.ARM_64,
                handler=handler,
                code=code,
                memory_size=memory,
                timeout=timeout,
                environment={**common_env, **env},
                tracing=lambda_.Tracing.ACTIVE,
                log_group=log_group,
            )
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["ssm:GetParametersByPath"],
                    resources=[
                        f"arn:aws:ssm:{Aws.REGION}:{Aws.ACCOUNT_ID}:parameter{ssm_prefix.rstrip('/')}"
                    ],
                )
            )
            fn.add_to_role_policy(
                iam.PolicyStatement(
                    actions=["kms:Decrypt"],
                    resources=[f"arn:aws:kms:{Aws.REGION}:{Aws.ACCOUNT_ID}:alias/aws/ssm"],
                    conditions={"StringEquals": {"kms:ViaService": f"ssm.{Aws.REGION}.amazonaws.com"}},
                )
            )
            if config["llmProvider"] == "bedrock":
                fn.add_to_role_policy(
                    iam.PolicyStatement(
                        actions=["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
                        resources=["*"],
                    )
                )
            return fn

        worker = function("Worker", "letterlens.handlers.worker", 512, Duration.seconds(120), {})
        status = function("Status", "letterlens.handlers.status", 256, Duration.seconds(30), {})
        retention = function("Retention", "letterlens.handlers.retention", 256, Duration.minutes(5), {})
        retention.add_to_role_policy(
            iam.PolicyStatement(actions=["s3:DeleteObject"], resources=[f"{letters_bucket_arn}/letters/*"])
        )

        # ------------------------------------------------------------------
        # Pipeline (Step Functions, Standard: 4,000 free state transitions per month)
        # ------------------------------------------------------------------
        def step(name: str, result_path: str | None = None) -> tasks.LambdaInvoke:
            task = tasks.LambdaInvoke(
                self,
                name.capitalize(),
                lambda_function=worker,
                payload=sfn.TaskInput.from_object(
                    {
                        "step": name,
                        "letter_id": sfn.JsonPath.string_at("$.letter_id"),
                        "language": sfn.JsonPath.string_at("$.language"),
                    }
                ),
                payload_response_only=True,
                result_path=result_path or sfn.JsonPath.DISCARD,
                retry_on_service_exceptions=True,
            )
            task.add_retry(
                errors=["States.TaskFailed", "States.Timeout"],
                max_attempts=2,
                interval=Duration.seconds(3),
                backoff_rate=2.0,
            )
            return task

        mark_failed = tasks.LambdaInvoke(
            self,
            "MarkFailed",
            lambda_function=status,
            payload=sfn.TaskInput.from_object(
                {
                    "letter_id": sfn.JsonPath.string_at("$.letter_id"),
                    "failed": True,
                    "error": sfn.JsonPath.string_at("$.error.Error"),
                }
            ),
            payload_response_only=True,
        ).next(sfn.Fail(self, "PipelineFailed"))
        mark_ready = tasks.LambdaInvoke(
            self,
            "MarkReady",
            lambda_function=status,
            payload=sfn.TaskInput.from_object(
                {
                    "letter_id": sfn.JsonPath.string_at("$.letter_id"),
                    "degraded": sfn.JsonPath.string_at("$.result.degraded"),
                }
            ),
            payload_response_only=True,
        )
        full = [step(s) for s in PIPELINE_STEPS]
        explain_task = step("explain", "$.result")
        for task in [*full, explain_task]:
            task.add_catch(mark_failed, result_path="$.error")
        chain: sfn.IChainable = full[0]
        for task in full[1:]:
            chain = chain.next(task)  # type: ignore[attr-defined]
        chain.next(explain_task)  # type: ignore[attr-defined]
        explain_task.next(mark_ready)
        definition = (
            sfn.Choice(self, "Mode")
            .when(sfn.Condition.string_equals("$.mode", "explain"), explain_task)
            .otherwise(full[0])
        )

        state_machine = sfn.StateMachine(
            self,
            "Pipeline",
            definition_body=sfn.DefinitionBody.from_chainable(definition),
            state_machine_type=sfn.StateMachineType.STANDARD,
            timeout=Duration.minutes(15),
            tracing_enabled=True,
            logs=sfn.LogOptions(
                destination=logs.LogGroup(
                    self,
                    "PipelineLogs",
                    retention=logs.RetentionDays.TWO_WEEKS,
                    removal_policy=RemovalPolicy.DESTROY,
                ),
                level=sfn.LogLevel.ERROR,
            ),
        )

        api = function(
            "Api",
            "letterlens.handlers.api",
            512,
            Duration.seconds(29),
            {
                "LETTERLENS_PIPELINE_RUNNER": "stepfunctions",
                "LETTERLENS_STATE_MACHINE_ARN": state_machine.state_machine_arn,
                "LETTERLENS_ORIGIN_VERIFY_SECRET": origin_secret,
            },
        )
        state_machine.grant_start_execution(api)
        api.add_to_role_policy(
            iam.PolicyStatement(
                actions=["s3:PutObject", "s3:GetObject", "s3:DeleteObject"],
                resources=[f"{letters_bucket_arn}/letters/*"],
            )
        )
        api_url = api.add_function_url(auth_type=lambda_.FunctionUrlAuthType.NONE)


"""Infrastructure assertions on the synthesized template."""

from __future__ import annotations

import json
from pathlib import Path

import aws_cdk as cdk
import pytest
from aws_cdk.assertions import Match, Template

from letterlens_infra.stack import LAMBDA_DIR, LetterLensStack

CONFIG = json.loads((Path(__file__).parents[1] / "cdk.json").read_text())["context"]["stages"]["prod"]


@pytest.fixture(scope="module")
def template() -> Template:
    if not LAMBDA_DIR.is_dir():
        LAMBDA_DIR.mkdir(parents=True)
        (LAMBDA_DIR / "placeholder.txt").write_text("synth only")
    app = cdk.App()
    stack = LetterLensStack(
        app, "T", stage="prod", config={**CONFIG, "originVerifySecret": "x", "alarmEmail": "ops@example.org"}
    )
    return Template.from_stack(stack)


def test_functions_are_arm64_python313_with_tracing(template: Template) -> None:
    functions = {
        k: v
        for k, v in template.find_resources("AWS::Lambda::Function").items()
        if str(v["Properties"].get("Handler", "")).startswith("letterlens.")
    }
    assert len(functions) == 4
    for fn in functions.values():
        assert fn["Properties"]["Runtime"] == "python3.13"
        assert fn["Properties"]["Architectures"] == ["arm64"]
        assert fn["Properties"]["TracingConfig"] == {"Mode": "Active"}


def test_buckets_block_public_access_and_encrypt(template: Template) -> None:
    for bucket in template.find_resources("AWS::S3::Bucket").values():
        props = bucket["Properties"]
        assert props["PublicAccessBlockConfiguration"]["BlockPublicPolicy"] is True
        assert "BucketEncryption" in props


def test_letter_images_expire(template: Template) -> None:
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": Match.array_with([Match.object_like({"Prefix": "letters/", "Status": "Enabled"})])
            }
        },
    )


def test_api_is_only_reachable_through_cloudfront_with_secret_header(template: Template) -> None:
    template.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "Origins": Match.array_with(
                        [
                            Match.object_like(
                                {
                                    "OriginCustomHeaders": [
                                        {"HeaderName": "X-Origin-Verify", "HeaderValue": "x"}
                                    ]
                                }
                            )
                        ]
                    )
                }
            )
        },
    )


def test_pipeline_is_standard_workflow_with_tracing(template: Template) -> None:
    template.has_resource_properties(
        "AWS::StepFunctions::StateMachine",
        {"StateMachineType": "STANDARD", "TracingConfiguration": {"Enabled": True}},
    )


def test_log_retention_is_bounded(template: Template) -> None:
    for group in template.find_resources("AWS::Logs::LogGroup").values():
        assert group["Properties"]["RetentionInDays"] <= 14


def test_budget_and_alarms_exist(template: Template) -> None:
    template.resource_count_is("AWS::Budgets::Budget", 1)
    assert len(template.find_resources("AWS::CloudWatch::Alarm")) <= 10  # free tier


def test_cognito_lite_plan(template: Template) -> None:
    template.has_resource_properties("AWS::Cognito::UserPool", {"UserPoolTier": "LITE"})


def test_functions_may_read_their_ssm_path_with_trailing_slash(template: Template) -> None:
    # Regression: the first deploy failed because only ".../parameter/letterlens/prod" was allowed,
    # while GetParametersByPath is checked against ".../parameter/letterlens/prod/".
    policies = template.find_resources("AWS::IAM::Policy")
    resources = [
        str(res)
        for policy in policies.values()
        for stmt in policy["Properties"]["PolicyDocument"]["Statement"]
        if "ssm:GetParametersByPath" in str(stmt["Action"])
        for res in (stmt["Resource"] if isinstance(stmt["Resource"], list) else [stmt["Resource"]])
    ]
    assert any("parameter/letterlens/prod/" in r for r in resources), resources


def test_web_client_uses_direct_password_auth_without_hosted_ui(template: Template) -> None:
    clients = template.find_resources("AWS::Cognito::UserPoolClient")
    web = next(c["Properties"] for k, c in clients.items() if k.startswith("UsersWebClient"))
    ios = next(c["Properties"] for k, c in clients.items() if k.startswith("UsersIosClient"))
    assert set(web["ExplicitAuthFlows"]) == {"ALLOW_USER_PASSWORD_AUTH", "ALLOW_REFRESH_TOKEN_AUTH"}
    assert web.get("AllowedOAuthFlowsUserPoolClient") in (None, False)
    assert "CallbackURLs" not in web
    assert web["PreventUserExistenceErrors"] == "ENABLED"
    assert web["EnableTokenRevocation"] is True
    # The iOS app keeps the hosted UI with PKCE and no password flow.
    assert ios["AllowedOAuthFlows"] == ["code"]
    assert "ALLOW_USER_PASSWORD_AUTH" not in ios.get("ExplicitAuthFlows", [])


def test_api_may_delete_cognito_users_for_account_deletion(template: Template) -> None:
    statements = [
        st
        for policy in template.find_resources("AWS::IAM::Policy").values()
        for st in policy["Properties"]["PolicyDocument"]["Statement"]
    ]
    deletes = [st for st in statements if st["Action"] == "cognito-idp:AdminDeleteUser"]
    assert len(deletes) == 1
    assert "Fn::GetAtt" in deletes[0]["Resource"]  # this pool only, not "*"


def test_own_domain_is_optional_and_needs_a_certificate() -> None:
    app = cdk.App()
    arn = "arn:aws:acm:us-east-1:123456789012:certificate/abc"
    stack = LetterLensStack(
        app,
        "D",
        stage="prod",
        config={
            **CONFIG,
            "originVerifySecret": "x",
            "alarmEmail": "",
            "domainNames": ["letterlens.de", "www.letterlens.de"],
            "certificateArn": arn,
        },
    )
    t = Template.from_stack(stack)
    t.has_resource_properties(
        "AWS::CloudFront::Distribution",
        {
            "DistributionConfig": Match.object_like(
                {
                    "Aliases": ["letterlens.de", "www.letterlens.de"],
                    "ViewerCertificate": Match.object_like(
                        {"AcmCertificateArn": arn, "MinimumProtocolVersion": "TLSv1.2_2021"}
                    ),
                }
            )
        },
    )
    t.has_output("SiteUrl", {"Value": "https://letterlens.de"})
    with pytest.raises(ValueError):
        LetterLensStack(
            cdk.App(),
            "E",
            stage="prod",
            config={**CONFIG, "originVerifySecret": "x", "domainNames": ["a.de"]},
        )

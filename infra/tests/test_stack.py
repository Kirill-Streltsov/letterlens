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



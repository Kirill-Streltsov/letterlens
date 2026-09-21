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



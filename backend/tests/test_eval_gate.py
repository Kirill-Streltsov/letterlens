"""The release gate must block a change that weakens the grounding check.

This test simulates a "bad pull request": the verifier trusts the model and marks
every fact as verified. With fault injection, invented dates then reach the user
as facts, and the gate must fail.
"""

from __future__ import annotations

from typing import Any

import pytest

from evals import run as ev
from letterlens.domain import FactStatus
from letterlens.grounding import verifier


def trusting_verify(extraction: Any, doc: Any) -> Any:
    facts = ORIGINAL_VERIFY(extraction, doc)
    return facts.model_copy(
        update={
            "deadlines": [d.model_copy(update={"status": FactStatus.VERIFIED}) for d in facts.deadlines],
            "amounts": [a.model_copy(update={"status": FactStatus.VERIFIED}) for a in facts.amounts],
        }
    )


ORIGINAL_VERIFY = verifier.verify


def chaos_report() -> dict[str, Any]:
    ctx = ev.make_context("chaos")
    letters = ev.load_golden()[:40]
    return {"suites": {"extraction": ev.suite_extraction(ctx, letters)}}


def test_gate_passes_with_real_verifier() -> None:
    assert ev.check_gates(chaos_report(), "chaos") == []


def test_gate_blocks_trusting_verifier(monkeypatch: pytest.MonkeyPatch) -> None:
    from letterlens.pipeline import steps

    monkeypatch.setattr(steps, "verify", trusting_verify)
    failures = ev.check_gates(chaos_report(), "chaos")
    assert any("unsafe_verified_dates" in f for f in failures)
    assert any("unsafe_verified_amounts" in f for f in failures)

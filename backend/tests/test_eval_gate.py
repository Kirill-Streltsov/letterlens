"""The release gate must block a change that weakens the grounding check.

This test simulates a "bad pull request": the verifier trusts the model and marks
every fact as verified. With fault injection, invented dates then reach the user
as facts, and the gate must fail.
"""

from __future__ import annotations

from typing import Any

import pytest

from evals import run as ev
from letterlens.domain import FactStatus, VerifiedAmount, VerifiedDeadline
from letterlens.grounding import verifier
from letterlens.grounding.german import parse_decimal_value, parse_iso_date


def trusting_verify(extraction: Any, doc: Any) -> Any:
    """A bad verifier: it takes the model's dates and amounts as they are and marks them verified."""
    facts = ORIGINAL_VERIFY(extraction, doc)
    deadlines = [
        VerifiedDeadline(
            id=f"d{i}",
            due_date=parse_iso_date(d.date),
            status=FactStatus.VERIFIED,
            is_estimate=False,
            description=d.description,
            line_ids=d.line_ids,
            source_text=None,
        )
        for i, d in enumerate(extraction.deadlines, 1)
        if d.date
    ]
    amounts = [
        VerifiedAmount(
            id=f"a{i}",
            value=v,
            currency="EUR",
            direction=a.direction if a.direction in {"to_pay", "to_receive"} else "info",
            status=FactStatus.VERIFIED,
            description=a.description,
            line_ids=a.line_ids,
        )
        for i, a in enumerate(extraction.amounts, 1)
        if (v := parse_decimal_value(a.value)) is not None
    ]
    return facts.model_copy(update={"deadlines": deadlines, "amounts": amounts})


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

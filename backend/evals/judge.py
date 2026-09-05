"""LLM-as-judge for translation faithfulness, and its validation.

The judge is trusted only if it separates faithful from corrupted summaries on a
calibration set. The calibration set is built by controlled perturbation, so the
true label of every pair is known: a changed date, amount or obligation must get
a low score; an unchanged summary must get a high score.
Replace or extend it with pairs labelled by bilingual reviewers when available
(evals/judge_calibration/reviewed.jsonl, same format).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from letterlens.domain import Frozen
from letterlens.llm import Gateway, Task

ROOT = Path(__file__).resolve().parent
REVIEWED = ROOT / "judge_calibration" / "reviewed.jsonl"
LANGUAGES = ROOT.parent / "src" / "letterlens" / "languages.yaml"
THRESHOLDS = ROOT / "thresholds.yaml"

REFERENCES = [
    "This letter is from the tax office. You must pay 1,523.00 euros by 12 February 2026. "
    "You can object within one month.",
    "The Jobcenter invites you to an appointment on 14 October 2026 at 10:00. Bring your CV and ID.",
    "Your landlord asks you to agree to a new rent of 645.00 euros from 1 March 2026. "
    "Please answer by 28 February 2026.",
    "The health insurer reminds you of unpaid contributions of 310.50 euros. Pay by 20 May 2026.",
]


def perturbations(text: str) -> list[tuple[str, bool]]:
    """(candidate, is_faithful) pairs derived from one reference."""
    sentences = text.split(". ")
    out = [(text, True), (". ".join(reversed(sentences)), True)]
    out.append((text.replace("2026", "2027", 1), False))
    out.append(
        (
            text.replace("must pay", "do not need to pay")
            .replace("Please answer", "You do not need to answer")
            .replace("Pay by", "Do not pay by")
            .replace("Bring", "Do not bring"),

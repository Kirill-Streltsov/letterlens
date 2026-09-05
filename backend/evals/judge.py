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


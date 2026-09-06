"""Evaluation suite and release gate.

Usage
  uv run python -m evals.run                       # offline profile (rules baseline), all suites
  uv run python -m evals.run --profile chaos       # fault injection: the model invents dates/amounts
  LETTERLENS_LLM_PROVIDER=mistral LETTERLENS_LLM_API_KEY=... \
  uv run python -m evals.run --profile live        # real model, adds the faithfulness suite
  uv run python -m evals.run --update-languages    # with --profile live: write language status

Exit code 1 when a gate in evals/thresholds.yaml fails. CI runs the offline and
chaos profiles on every pull request (.github/workflows/ci.yml).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any


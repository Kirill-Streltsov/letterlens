"""Output languages and the fixed safety texts in each language.

A language is ENABLED only when its faithfulness score in the latest
evaluation is at or above the threshold (evals/thresholds.yaml). The
evaluation job updates ``status`` in languages.yaml; this module reads it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from functools import lru_cache
from pathlib import Path

import yaml

from letterlens.config import get_settings


class LanguageStatus(StrEnum):
    ENABLED = "enabled"
    EXPERIMENTAL = "experimental"  # visible with a warning; below threshold or not yet measured
    DISABLED = "disabled"



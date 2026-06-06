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


@dataclass(frozen=True, slots=True)
class Language:
    code: str
    name: str
    native_name: str
    rtl: bool
    status: LanguageStatus
    faithfulness: float | None


_DEFAULT_FILE = Path(__file__).with_name("languages.yaml")


@lru_cache(maxsize=1)
def languages() -> dict[str, Language]:
    path = Path(get_settings().languages_file or _DEFAULT_FILE)
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        code: Language(
            code=code,
            name=item["name"],
            native_name=item["native_name"],
            rtl=bool(item.get("rtl", False)),
            status=LanguageStatus(item["status"]),
            faithfulness=item.get("faithfulness"),
        )
        for code, item in raw["languages"].items()
    }



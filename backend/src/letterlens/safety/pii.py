"""Reversible pseudonymization of personal data before text reaches a model.

The model sees placeholders such as ``[IBAN_1]``. After the model call the
vault puts the original values back. The vault lives only in memory for the
duration of one pipeline step and is never stored or logged.

Limitations (documented in docs/security/data-protection.md): person names
are detected only in the address block, by heuristics.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from letterlens.domain import LetterDocument, OcrLine


@dataclass(frozen=True, slots=True)
class Rule:
    kind: str
    pattern: re.Pattern[str]
    group: int = 0



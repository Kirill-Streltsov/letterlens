"""Synthetic German official letters with exact ground-truth labels.

All names, addresses and numbers are invented. The generator is
deterministic for a given seed, so the golden set is reproducible.

Each template family has phrase variants. The evaluation splits by
template family, so classifier scores measure generalization to unseen
layouts, not memorized templates.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import date, timedelta
from decimal import Decimal

from letterlens.domain import LetterType

# --------------------------------------------------------------------------
# Labels
# --------------------------------------------------------------------------



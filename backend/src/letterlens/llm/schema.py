"""Convert pydantic models to strict JSON schemas for structured outputs.

Providers with strict structured outputs (Claude, Mistral, OpenAI-compatible)
need: no $ref, ``additionalProperties: false`` on every object, and every
property listed in ``required``. Optional fields stay nullable.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

_DROP = {"title", "default", "examples"}



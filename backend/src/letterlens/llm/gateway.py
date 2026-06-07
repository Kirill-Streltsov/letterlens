"""LLM gateway: the only path from application code to a model.

Responsibilities
- Route each task to a model chain (primary, then fallbacks).
- Enforce budgets before every call (monthly spend, tokens per user per day).
- Retry transient errors with exponential backoff and jitter.
- Validate output against a strict schema; one repair attempt on invalid JSON.
- Record every call in the cost ledger: tokens, list price, latency, prompt version.
"""

from __future__ import annotations

import json
import logging
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

from pydantic import BaseModel, ValidationError


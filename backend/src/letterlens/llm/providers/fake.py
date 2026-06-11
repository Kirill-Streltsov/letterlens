"""Offline, deterministic provider for local development, tests and CI.

It never calls a network. It produces schema-valid outputs from the
structured ``context`` of each request, using the rule-based extractor and
templates. Its quality is the "rules baseline" in evaluation reports.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any

from letterlens.domain import LetterDocument
from letterlens.extraction.rules import extract_with_rules
from letterlens.llm.types import LLMRequest, LLMResponse, PermanentError, Task
from letterlens.safety.guardrail import Verdict, check_question_rules

_DIRECTION_TEXT = {"to_pay": "to pay", "to_receive": "you receive", "info": "for information"}



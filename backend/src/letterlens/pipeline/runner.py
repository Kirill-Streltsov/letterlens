"""Pipeline runners.

InProcessRunner: runs every step in the calling process (dev, tests).
StepFunctionsRunner: starts an AWS Step Functions execution; each state calls
``run_step`` in the worker Lambda (letterlens.handlers.worker).
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Sequence
from typing import Any, Protocol

from letterlens.domain import LetterStatus
from letterlens.pipeline.state import STEPS, PipelineState, StateStore
from letterlens.pipeline.steps import STEP_FUNCTIONS, PipelineDeps, explain

log = logging.getLogger(__name__)

EXPLAIN_ONLY = ("explain", "finalize")



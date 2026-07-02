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


def run_step(
    step: str, letter_id: str, store: StateStore, deps: PipelineDeps, language: str | None = None
) -> PipelineState:
    state = store.load_state(letter_id)
    started = time.perf_counter()
    if step == "explain":
        state = explain(state, deps, language)
    else:
        state = STEP_FUNCTIONS[step](state, deps)
    store.save_state(state)
    log.info(
        "pipeline step done",
        extra={
            "letter_id": letter_id,
            "step": step,
            "ms": int((time.perf_counter() - started) * 1000),
            "degraded": state.degraded,
        },
    )
    return state


class Runner(Protocol):
    def start(
        self, letter_id: str, steps: Sequence[str] = STEPS, language: str | None = None
    ) -> None: ...



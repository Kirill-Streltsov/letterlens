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
    state = explain(state, deps, language) if step == "explain" else STEP_FUNCTIONS[step](state, deps)
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
    def start(self, letter_id: str, steps: Sequence[str] = STEPS, language: str | None = None) -> None: ...


class InProcessRunner:
    def __init__(self, store: StateStore, deps_factory: Callable[[], PipelineDeps]) -> None:
        self.store = store
        self.deps_factory = deps_factory

    def start(self, letter_id: str, steps: Sequence[str] = STEPS, language: str | None = None) -> None:
        deps = self.deps_factory()
        self.store.set_status(letter_id, LetterStatus.PROCESSING)
        try:
            for step in steps:
                run_step(step, letter_id, self.store, deps, language)
        except Exception as exc:
            log.exception("pipeline failed", extra={"letter_id": letter_id})
            self.store.set_status(letter_id, LetterStatus.FAILED, type(exc).__name__)
            return
        self.store.set_status(letter_id, LetterStatus.READY)


class StepFunctionsRunner:
    def __init__(self, state_machine_arn: str, client: Any = None) -> None:
        if client is None:
            import boto3

            client = boto3.client("stepfunctions")
        self.client = client
        self.arn = state_machine_arn

    def start(self, letter_id: str, steps: Sequence[str] = STEPS, language: str | None = None) -> None:
        mode = "explain" if tuple(steps) == EXPLAIN_ONLY else "full"
        payload = {"letter_id": letter_id, "mode": mode, "language": language}
        self.client.start_execution(
            stateMachineArn=self.arn,
            name=f"{letter_id}-{int(time.time() * 1000)}",
            input=json.dumps(payload),
        )

"""AWS Lambda entry points.

api:       Lambda Function URL -> FastAPI (through Mangum)
worker:    one Step Functions task state = one pipeline step
status:    Step Functions success/failure states update the letter status
retention: EventBridge Scheduler, daily: delete expired letters and images
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

from letterlens.config import get_settings
from letterlens.container import Container
from letterlens.domain import LetterStatus
from letterlens.observability import configure_logging, emit_metric

log = logging.getLogger("letterlens.handlers")


@lru_cache(maxsize=1)
def _container() -> Container:
    from letterlens.secrets import load_ssm_into_env

    load_ssm_into_env()
    settings = get_settings()
    configure_logging(settings.log_level)
    return Container(settings)


@lru_cache(maxsize=1)
def _asgi() -> Any:
    from mangum import Mangum

    from letterlens.api.app import create_app

    return Mangum(create_app(container=_container()), lifespan="off")


def api(event: dict[str, Any], context: Any) -> dict[str, Any]:
    result: dict[str, Any] = _asgi()(event, context)
    return result


def worker(event: dict[str, Any], context: Any) -> dict[str, Any]:
    from letterlens.pipeline.runner import run_step

    c = _container()
    state = run_step(event["step"], event["letter_id"], c.state_store, c.deps, event.get("language"))
    if event["step"] == "verify" and state.facts is not None:
        emit_metric("GroundingRate", state.facts.grounding_rate)
    return {"letter_id": event["letter_id"], "degraded": state.degraded}


def status(event: dict[str, Any], context: Any) -> dict[str, Any]:
    c = _container()
    letter_id = event["letter_id"]
    if event.get("failed"):
        error = str(event.get("error", "PipelineError"))[:120]
        c.state_store.set_status(letter_id, LetterStatus.FAILED, error)
        emit_metric("PipelineFailed", 1)
    else:
        c.state_store.set_status(letter_id, LetterStatus.READY, None)
        emit_metric("PipelineSucceeded", 1)
        if event.get("degraded"):
            emit_metric("PipelineDegraded", 1)
    return {"letter_id": letter_id}


def retention(event: dict[str, Any], context: Any) -> dict[str, Any]:
    from letterlens.db import DbContext
    from letterlens.db.repo import audit, purge_expired

    c = _container()
    total = 0
    while True:
        with c.db.session(DbContext.as_system()) as conn:
            deleted, keys = purge_expired(conn)
            if deleted:
                audit(conn, None, "retention.purge", "letters", "batch", details={"count": deleted})
        c.storage.delete(keys)
        total += deleted
        if deleted < 500:
            break
    log.info("retention done", extra={"deleted": total})
    return {"deleted": total}

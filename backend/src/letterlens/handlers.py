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



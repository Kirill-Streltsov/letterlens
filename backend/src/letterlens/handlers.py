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



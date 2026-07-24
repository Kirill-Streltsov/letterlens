"""Structured JSON logs, CloudWatch EMF metrics and request correlation.

Logs are JSON lines. CloudWatch Logs Insights queries them (docs/operations/runbook.md).
Metrics use the Embedded Metric Format: a log line that CloudWatch turns into a
metric. The metric set is small on purpose: the free tier includes 10 custom metrics.
LLM fields use the OpenTelemetry GenAI attribute names (gen_ai.*), so an OTel
exporter can be added without renaming fields.

Rule: log lines never contain letter text, questions, answers or names.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

NAMESPACE = "LetterLens"
METRICS = {
    "LettersCreated": "Count",
    "PipelineSucceeded": "Count",
    "PipelineFailed": "Count",
    "PipelineDegraded": "Count",
    "GroundingRate": "None",
    "LLMListPriceUSD": "None",
    "GuardrailBlocked": "Count",
    "QuestionsAnswered": "Count",
    "LatencyMs": "Milliseconds",
}

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

_RESERVED = set(logging.LogRecord("", 0, "", 0, "", (), None).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": round(record.created, 3),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if rid := request_id_var.get():
            payload["request_id"] = rid
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in ("httpx", "httpcore", "botocore", "urllib3", "psycopg.pool"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def emit_metric(name: str, value: float, **properties: Any) -> None:
    """Write one EMF record. Properties are searchable fields, not metric dimensions."""
    if name not in METRICS:
        raise ValueError(f"unknown metric {name}; add it to METRICS (free tier has 10)")
    record = {
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [
                {
                    "Namespace": NAMESPACE,
                    "Dimensions": [["Service"]],

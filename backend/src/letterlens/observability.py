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


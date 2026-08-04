"""FastAPI application factory."""

from __future__ import annotations

import logging
import time
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from letterlens.api.deps import Services
from letterlens.api.errors import ApiError
from letterlens.api.routes import public, router
from letterlens.config import Environment, Settings, get_settings
from letterlens.container import Container
from letterlens.observability import configure_logging, request_id_var

log = logging.getLogger("letterlens.http")

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
}



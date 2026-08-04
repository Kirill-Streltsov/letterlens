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


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    container = container or Container(settings)

    app = FastAPI(
        title="LetterLens API",
        version="1.0.0",
        description=(
            "Explains German official letters in the reader's language. Facts are grounded in "
            "source lines; dates that cannot be grounded are marked 'please check'."
        ),
        docs_url="/docs" if settings.env is not Environment.PROD else None,
        redoc_url=None,
    )
    app.state.services = Services(container)

    if settings.env is not Environment.PROD:
        # In production the web app and the API share one CloudFront origin: no CORS.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.public_web_url],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    @app.middleware("http")
    async def context(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        token = request_id_var.set(rid[:64])
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-Id"] = rid[:64]
        for key, value in SECURITY_HEADERS.items():
            response.headers.setdefault(key, value)
        log.info(
            "request",
            extra={
                "request_id": rid[:64],
                "method": request.method,
                # The route template, not the raw path: ids are not logged.
                "route": getattr(request.scope.get("route"), "path", "unknown"),
                "status": response.status_code,
                "ms": int((time.perf_counter() - started) * 1000),
            },
        )
        return response


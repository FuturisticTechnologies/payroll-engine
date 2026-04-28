"""FastAPI application entrypoint.

Wires the API router, middleware, exception handlers and lifecycle hooks.
"""
from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import init_local_database
from app.core.logging import configure_logging, get_logger

settings = get_settings()
configure_logging(settings.app_env, settings.app_debug)
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info(
        "application.startup",
        env=settings.app_env,
        version=__version__,
    )
    await init_local_database()
    yield
    log.info("application.shutdown")


app = FastAPI(
    title="PayrollFuturistic API",
    description=(
        "UK-compliant payroll SaaS platform. HMRC (PAYE, NI, RTI), "
        "statutory payments, pension auto-enrolment, UK GDPR."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    clear_contextvars()
    bind_contextvars(
        request_id=request_id,
        method=request.method,
        path=request.url.path,
    )

    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "request.failed",
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
        )
        clear_contextvars()
        raise

    response.headers["X-Request-ID"] = request_id
    log.info(
        "request.completed",
        status_code=response.status_code,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
    clear_contextvars()
    return response


app.include_router(api_router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {
        "name": "PayrollFuturistic API",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/v1/health",
    }

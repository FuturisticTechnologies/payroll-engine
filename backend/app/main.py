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
from starlette.responses import JSONResponse, Response
from structlog.contextvars import bind_contextvars, clear_contextvars

from app import __version__
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import init_local_database
from app.core.logging import configure_logging, get_logger
from app.core.openapi import (
    CONTACT,
    LICENSE,
    OPENAPI_TAGS,
    SERVERS,
    SERVICE_DESCRIPTION,
    SERVICE_SUMMARY,
    SERVICE_TITLE,
)

settings = get_settings()
configure_logging(settings.app_env, settings.app_debug)
log = get_logger(__name__)

_UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_CSRF_EXEMPT_PATHS = {"/api/v1/auth/csrf", "/api/v1/auth/login"}


def _apply_security_headers(response: Response) -> None:
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    response.headers.setdefault(
        "Content-Security-Policy",
        "default-src 'self'; "
        "img-src 'self' data:; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self' http://localhost:4200 http://127.0.0.1:4200; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'",
    )
    if settings.app_env == "production":
        response.headers.setdefault(
            "Strict-Transport-Security",
            "max-age=31536000; includeSubDomains",
        )


def _csrf_failed_response(request_id: str) -> JSONResponse:
    response = JSONResponse(
        status_code=403,
        content={"detail": "CSRF token missing or invalid"},
    )
    response.headers["X-Request-ID"] = request_id
    _apply_security_headers(response)
    return response


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
    title=SERVICE_TITLE,
    summary=SERVICE_SUMMARY,
    description=SERVICE_DESCRIPTION,
    version=__version__,
    contact=CONTACT,
    license_info=LICENSE,
    openapi_tags=OPENAPI_TAGS,
    servers=SERVERS,
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

    authorization = request.headers.get("Authorization", "")
    bearer_request = authorization.lower().startswith("bearer ")
    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if (
        settings.app_env == "production"
        and request.method in _UNSAFE_METHODS
        and request.url.path not in _CSRF_EXEMPT_PATHS
        and not bearer_request
        and (not csrf_cookie or csrf_cookie != csrf_header)
    ):
        clear_contextvars()
        return _csrf_failed_response(request_id)

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
    _apply_security_headers(response)
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
        "name": SERVICE_TITLE,
        "version": __version__,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/api/v1/health",
    }

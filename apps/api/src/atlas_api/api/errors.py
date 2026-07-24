"""Exception handlers mapping domain errors to HTTP responses."""

from __future__ import annotations

import logging

from atlas_catalog.domain import ConflictError as CatalogConflict
from atlas_catalog.domain import ValidationError as CatalogValidation
from atlas_core.errors import (
    AtlasError,
    ConfigError,
    DependencyError,
    NotFoundError,
    UnauthorizedError,
)
from atlas_core.errors import (
    ForbiddenError as CoreForbidden,
)
from atlas_identity.application.service import (
    AuthError,
    ConflictError,
    ForbiddenError,
    RateLimitError,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Attach baseline security headers to every response."""

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy", "geolocation=(), microphone=(), camera=()"
        )
        if request.url.scheme == "https":
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON error handlers."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc), "type": "not_found"})

    @app.exception_handler(AuthError)
    async def auth_handler(_: Request, exc: AuthError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc), "type": "unauthorized"})

    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(_: Request, exc: UnauthorizedError) -> JSONResponse:
        return JSONResponse(status_code=401, content={"detail": str(exc), "type": "unauthorized"})

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(_: Request, exc: ForbiddenError) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc), "type": "forbidden"})

    @app.exception_handler(CoreForbidden)
    async def core_forbidden_handler(_: Request, exc: CoreForbidden) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc), "type": "forbidden"})

    @app.exception_handler(ConflictError)
    async def conflict_handler(_: Request, exc: ConflictError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc), "type": "conflict"})

    @app.exception_handler(CatalogConflict)
    async def catalog_conflict_handler(_: Request, exc: CatalogConflict) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": str(exc), "type": "conflict"})

    @app.exception_handler(CatalogValidation)
    async def catalog_validation_handler(_: Request, exc: CatalogValidation) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc), "type": "validation_error"})

    @app.exception_handler(RateLimitError)
    async def rate_limit_handler(_: Request, exc: RateLimitError) -> JSONResponse:
        return JSONResponse(status_code=429, content={"detail": str(exc), "type": "rate_limited"})

    @app.exception_handler(ConfigError)
    async def config_handler(_: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc), "type": "config_error"})

    @app.exception_handler(DependencyError)
    async def dependency_handler(_: Request, exc: DependencyError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": str(exc), "type": "dependency_error"}
        )

    @app.exception_handler(ValueError)
    async def value_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc), "type": "validation_error"})

    @app.exception_handler(AtlasError)
    async def atlas_handler(_: Request, exc: AtlasError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc), "type": "atlas_error"})

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "type": "internal_error"},
        )

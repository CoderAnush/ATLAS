"""Exception handlers mapping domain errors to HTTP responses."""

from __future__ import annotations

import logging

from atlas_core.errors import AtlasError, ConfigError, DependencyError, NotFoundError
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register consistent JSON error handlers."""

    @app.exception_handler(NotFoundError)
    async def not_found_handler(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc), "type": "not_found"})

    @app.exception_handler(ConfigError)
    async def config_handler(_: Request, exc: ConfigError) -> JSONResponse:
        return JSONResponse(status_code=500, content={"detail": str(exc), "type": "config_error"})

    @app.exception_handler(DependencyError)
    async def dependency_handler(_: Request, exc: DependencyError) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": str(exc), "type": "dependency_error"}
        )

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

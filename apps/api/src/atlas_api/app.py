"""Application factory for the ATLAS FastAPI service."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from atlas_telemetry.logging import configure_logging
from atlas_telemetry.tracing import setup_tracing
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from atlas_api import __version__
from atlas_api.api.errors import register_exception_handlers
from atlas_api.api.v1 import api_v1_router, root_health_router
from atlas_api.config import Settings, get_settings
from atlas_api.di import build_container
from atlas_api.middleware import RequestContextMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Start and stop application resources."""
    settings: Settings = app.state.settings
    logger.info("Starting ATLAS API env=%s version=%s", settings.atlas_env, __version__)
    try:
        client = app.state.container.minio_client
        bucket = settings.minio_bucket
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info("Created MinIO bucket %s", bucket)
    except Exception as exc:  # noqa: BLE001
        logger.warning("MinIO bucket ensure failed: %s", exc)
    yield
    logger.info("Shutting down ATLAS API")
    try:
        app.state.container.redis.close()
    except Exception:  # noqa: BLE001
        pass
    try:
        app.state.container.engine.dispose()
    except Exception:  # noqa: BLE001
        pass


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or get_settings()
    configure_logging(settings.atlas_log_level, json_logs=settings.atlas_json_logs)
    if settings.otel_traces_enabled:
        setup_tracing(settings.atlas_service_name, endpoint=settings.otel_exporter_otlp_endpoint)

    app = FastAPI(
        title="ATLAS API",
        description="Autonomous Training, Learning And Serving — platform foundation",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )
    app.state.settings = settings
    app.state.container = build_container(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(root_health_router)
    app.include_router(api_v1_router)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": "ATLAS API",
            "version": __version__,
            "docs": "/docs",
            "health": "/health",
        }

    return app

"""Health, readiness, liveness, and metrics endpoints."""

from __future__ import annotations

import logging

import httpx
from atlas_api import __version__
from atlas_api.config import Settings
from atlas_contracts.health import ComponentHealth, HealthResponse, HealthStatus, ReadinessResponse
from atlas_db.health import check_database
from atlas_storage.health import check_minio
from atlas_telemetry.metrics import generate_metrics
from fastapi import APIRouter, Request, Response
from redis import Redis

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


def _component(name: str, ok: bool, detail: str | None = None) -> ComponentHealth:
    return ComponentHealth(
        name=name,
        status=HealthStatus.HEALTHY if ok else HealthStatus.UNHEALTHY,
        detail=detail,
    )


@router.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """Liveness-oriented health (process is up)."""
    settings: Settings = request.app.state.settings
    return HealthResponse(
        status=HealthStatus.HEALTHY,
        service=settings.atlas_service_name,
        version=__version__,
        components=[_component("api", True)],
    )


@router.get("/health/live", response_model=HealthResponse)
async def liveness(request: Request) -> HealthResponse:
    """Kubernetes liveness probe."""
    return await health(request)


@router.get("/health/ready", response_model=ReadinessResponse)
async def readiness(request: Request) -> ReadinessResponse:
    """Readiness probe checking core dependencies."""
    container = request.app.state.container
    settings: Settings = request.app.state.settings
    components: list[ComponentHealth] = []

    try:
        ok = check_database(container.engine)
        components.append(_component("postgres", ok))
    except Exception as exc:  # noqa: BLE001 - health must not raise
        logger.warning("postgres health failed: %s", exc)
        components.append(_component("postgres", False, str(exc)))

    try:
        redis_client: Redis[str] = container.redis
        ok = bool(redis_client.ping())
        components.append(_component("redis", ok))
    except Exception as exc:  # noqa: BLE001
        components.append(_component("redis", False, str(exc)))

    try:
        ok = check_minio(container.minio_client)
        components.append(_component("minio", ok))
    except Exception as exc:  # noqa: BLE001
        components.append(_component("minio", False, str(exc)))

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            resp = await client.get(f"{settings.mlflow_tracking_uri.rstrip('/')}/health")
            ok = resp.status_code < 500
        components.append(_component("mlflow", ok, f"status={resp.status_code}"))
    except Exception as exc:  # noqa: BLE001
        components.append(_component("mlflow", False, str(exc)))

    critical_ok = all(
        component.status == HealthStatus.HEALTHY
        for component in components
        if component.name in {"postgres", "redis"}
    )
    return ReadinessResponse(
        status=HealthStatus.HEALTHY if critical_ok else HealthStatus.UNHEALTHY,
        ready=critical_ok,
        components=components,
        detail=None if critical_ok else "One or more critical dependencies are unhealthy",
        metadata={"service": settings.atlas_service_name, "version": __version__},
    )


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics exposition."""
    payload, content_type = generate_metrics()
    return Response(content=payload, media_type=content_type)

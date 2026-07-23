"""Health-check response contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    """Possible health states for a service or dependency."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health information for one named component."""

    name: str
    status: HealthStatus
    detail: str | None = None


class HealthResponse(BaseModel):
    """Liveness-oriented health response."""

    status: HealthStatus
    service: str
    version: str
    components: list[ComponentHealth] = Field(default_factory=list)


class ReadinessResponse(BaseModel):
    """Readiness response including dependency status."""

    status: HealthStatus
    ready: bool
    components: list[ComponentHealth] = Field(default_factory=list)
    detail: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

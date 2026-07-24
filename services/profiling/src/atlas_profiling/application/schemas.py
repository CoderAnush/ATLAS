"""Profiling application schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


class JobResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    progress: int
    error_message: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProfileSummaryResponse(BaseModel):
    dataset_id: uuid.UUID
    dataset_version: int
    rows: int
    columns: int
    problem_type: str
    target_column: str | None
    target_confidence: float | None
    health: str
    quality_overall: float
    summary: str


class ProfileResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version: int
    overview: dict[str, Any]
    summary: str
    problem_type: str
    target: dict[str, Any]
    quality: dict[str, Any]
    leakage: dict[str, Any]
    recommendations: list[str]
    columns: list[dict[str, Any]]


class RunProfilingResponse(BaseModel):
    job_id: uuid.UUID
    status: str

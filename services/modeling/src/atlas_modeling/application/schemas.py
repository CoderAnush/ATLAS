"""Modeling application schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunTrainingRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class RunTrainingResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    feature_set_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version: int
    status: str
    progress: int
    eta_seconds: int | None = None
    error_message: str | None = None
    config_json: dict[str, Any]
    created_by_user_id: uuid.UUID
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class ModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    name: str
    problem_type: str
    algorithm: str
    target_column: str
    status: str
    summary: str
    feature_count: int
    model_size_bytes: int
    training_seconds: float
    warnings_json: list[Any]
    created_at: datetime


class ApproveTrainingRequest(BaseModel):
    job_id: uuid.UUID
    note: str = ""


class RejectTrainingRequest(BaseModel):
    job_id: uuid.UUID
    reason: str = ""


class ExportTrainingRequest(BaseModel):
    job_id: uuid.UUID


class SearchTrainingRequest(BaseModel):
    query: str
    limit: int = 20

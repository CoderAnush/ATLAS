"""Feature store application schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunFeaturesRequest(BaseModel):
    config: dict[str, Any] = Field(default_factory=dict)


class RunFeaturesResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version: int
    status: str
    progress: int
    error_message: str | None = None
    config: dict[str, Any]
    created_by_user_id: uuid.UUID
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class FeatureSetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    dataset_id: uuid.UUID
    name: str
    status: str
    summary: str
    selected_features: list[Any]
    rejected_features: list[Any]
    quality_score: float
    rows: int
    columns: int
    output_dataset_version: int | None = None
    created_at: datetime


class ApproveRequest(BaseModel):
    job_id: uuid.UUID
    edited_steps: list[dict[str, Any]] | None = None
    selected_features: list[str] | None = None


class RejectRequest(BaseModel):
    job_id: uuid.UUID
    reason: str = ""


class ExportRequest(BaseModel):
    job_id: uuid.UUID


class SearchRequest(BaseModel):
    query: str
    tags: list[str] | None = None
    limit: int = 20


class FeatureSummaryResponse(BaseModel):
    dataset_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    summary: str
    feature_set_id: uuid.UUID | None = None
    quality_score: float | None = None
    recommendations: list[dict[str, Any]] | None = None

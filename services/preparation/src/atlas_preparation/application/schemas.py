"""Preparation application schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RunPreparationRequest(BaseModel):
    strategies: dict[str, Any] = Field(default_factory=dict)


class RunPreparationResponse(BaseModel):
    job_id: uuid.UUID
    status: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dataset_id: uuid.UUID
    dataset_version: int
    status: str
    progress: int
    error_message: str | None = None
    created_at: datetime


class ApproveRequest(BaseModel):
    job_id: uuid.UUID
    edited_steps: list[dict[str, Any]] | None = None


class RejectRequest(BaseModel):
    job_id: uuid.UUID
    reason: str = ""


class PreparationSummaryResponse(BaseModel):
    dataset_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    summary: str
    quality_before: float | None = None
    quality_after: float | None = None
    output_version: int | None = None
    recipe_id: uuid.UUID | None = None
    report_id: uuid.UUID | None = None


class ExportRequest(BaseModel):
    job_id: uuid.UUID


class ExportResponse(BaseModel):
    job_id: uuid.UUID
    status: str
    data_url: str | None = None
    expires_in_seconds: int | None = None
    recipe: dict[str, Any] | None = None

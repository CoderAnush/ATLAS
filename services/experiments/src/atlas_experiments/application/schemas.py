"""Pydantic schemas for experiment APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    name: str
    description: str
    status: str
    group_name: str | None = None
    dataset_id: UUID | None = None
    feature_set_id: UUID | None = None
    algorithm: str | None = None
    problem_type: str | None = None
    best_run_id: UUID | None = None
    best_metric_name: str | None = None
    best_metric_value: float | None = None
    run_count: int
    pinned: bool
    created_by_user_id: UUID
    created_at: datetime


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    name: str
    status: str
    source: str
    training_job_id: UUID | None = None
    hpo_job_id: UUID | None = None
    hpo_study_id: UUID | None = None
    dataset_id: UUID | None = None
    dataset_version: int | None = None
    feature_set_id: UUID | None = None
    algorithm: str | None = None
    problem_type: str | None = None
    random_seed: int | None = None
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    runtime_seconds: float | None = None
    pinned: bool
    favorite: bool
    archived: bool
    metrics_json: dict[str, Any]
    hyperparameters_json: dict[str, Any]
    visualizations_json: dict[str, Any]
    created_at: datetime


class LeaderboardEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    experiment_id: UUID
    run_id: UUID
    algorithm: str | None = None
    accuracy: float | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    loss: float | None = None
    runtime_seconds: float | None = None
    rank_score: float | None = None
    created_at: datetime


class SearchExperimentsRequest(BaseModel):
    query: str = ""
    algorithm: str | None = None
    status: str | None = None
    tag: str | None = None
    owner_id: UUID | None = None
    dataset_id: UUID | None = None
    limit: int = Field(default=50, ge=1, le=500)


class CompareRunsRequest(BaseModel):
    run_ids: list[UUID] = Field(min_length=2, max_length=20)
    name: str = "comparison"


class FavoriteRequest(BaseModel):
    run_id: UUID


class ArchiveRequest(BaseModel):
    experiment_id: UUID | None = None
    run_id: UUID | None = None


class CloneExperimentRequest(BaseModel):
    experiment_id: UUID
    name: str | None = None


class ExportExperimentRequest(BaseModel):
    experiment_id: UUID

"""Pydantic schemas for HPO APIs."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RunHpoRequest(BaseModel):
    optimizer: str = "optuna"
    metric_objective: str = "accuracy"
    budget: dict[str, Any] = Field(
        default_factory=lambda: {"max_trials": 10, "parallel_workers": 1}
    )
    config: dict[str, Any] = Field(default_factory=dict)


class RunHpoResponse(BaseModel):
    job_id: UUID
    status: str


class JobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    training_job_id: UUID
    status: str
    progress: int
    optimizer: str
    metric_objective: str
    best_score: float | None = None
    trials_completed: int
    remaining_trials: int | None = None
    error_message: str | None = None
    created_at: datetime


class StudyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_id: UUID
    study_name: str
    optimizer: str
    direction: str
    status: str
    problem_type: str
    algorithm: str
    metric_objective: str
    feature_count: int
    total_trials: int
    completed_trials: int
    pruned_trials: int
    best_trial_number: int | None = None
    best_score: float | None = None
    best_params_json: dict[str, Any]
    report_json: dict[str, Any]
    history_json: dict[str, Any]
    created_at: datetime


class SearchHpoRequest(BaseModel):
    query: str = ""
    limit: int = 20


class ApproveHpoRequest(BaseModel):
    study_id: UUID
    note: str = ""


class RejectHpoRequest(BaseModel):
    study_id: UUID
    reason: str = ""


class ExportHpoRequest(BaseModel):
    study_id: UUID

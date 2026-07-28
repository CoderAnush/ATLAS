"""Experiments HTTP API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter

from atlas_experiments.api.deps import ExperimentsSvc
from atlas_experiments.application.schemas import (
    ArchiveRequest,
    CloneExperimentRequest,
    CompareRunsRequest,
    ExperimentResponse,
    ExportExperimentRequest,
    FavoriteRequest,
    LeaderboardEntryResponse,
    RunResponse,
    SearchExperimentsRequest,
)

router = APIRouter(prefix="/experiments", tags=["experiments"])


@router.get("/", response_model=list[ExperimentResponse])
def list_experiments(ctx: CurrentUser, svc: ExperimentsSvc) -> list[ExperimentResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        ExperimentResponse.model_validate(item)
        for item in svc.list_experiments(ctx.user_id, ctx.organization_id)
    ]


@router.get("/runs", response_model=list[RunResponse])
def list_runs(
    ctx: CurrentUser,
    svc: ExperimentsSvc,
    experiment_id: UUID | None = None,
) -> list[RunResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        RunResponse.model_validate(item)
        for item in svc.list_runs(ctx.user_id, ctx.organization_id, experiment_id=experiment_id)
    ]


@router.get("/runs/{id}", response_model=dict[str, Any])
def get_run(id: UUID, ctx: CurrentUser, svc: ExperimentsSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    detail = svc.get_run_detail(ctx.user_id, ctx.organization_id, id)
    return {
        "run": RunResponse.model_validate(detail["run"]),
        "metrics": [
            {
                "metric_name": m.metric_name,
                "metric_value": m.metric_value,
                "step": m.step,
                "split": m.split,
            }
            for m in detail["metrics"]
        ],
        "artifacts": [
            {
                "id": str(a.id),
                "artifact_type": a.artifact_type,
                "name": a.name,
                "storage_key": a.storage_key,
                "size_bytes": a.size_bytes,
                "checksum_sha256": a.checksum_sha256,
            }
            for a in detail["artifacts"]
        ],
        "history": [
            {
                "event": h.event,
                "message": h.message,
                "created_at": h.created_at.isoformat(),
            }
            for h in detail["history"]
        ],
    }


@router.get("/leaderboard", response_model=list[LeaderboardEntryResponse])
def leaderboard(ctx: CurrentUser, svc: ExperimentsSvc) -> list[LeaderboardEntryResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        LeaderboardEntryResponse.model_validate(item)
        for item in svc.leaderboard(ctx.user_id, ctx.organization_id)
    ]


@router.get("/{id}", response_model=dict[str, Any])
def get_experiment(id: UUID, ctx: CurrentUser, svc: ExperimentsSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    experiment = svc.get_experiment(ctx.user_id, ctx.organization_id, id)
    runs = svc.list_runs(ctx.user_id, ctx.organization_id, experiment_id=id)
    return {
        "experiment": ExperimentResponse.model_validate(experiment),
        "runs": [RunResponse.model_validate(run) for run in runs],
        "history": [
            {
                "event": h.event,
                "message": h.message,
                "created_at": h.created_at.isoformat(),
            }
            for h in svc.repo.list_history(ctx.organization_id, id)
        ],
        "tags": [
            {"key": t.tag_key, "value": t.tag_value}
            for t in svc.repo.list_tags(ctx.organization_id, id)
        ],
    }


@router.post("/search", response_model=list[ExperimentResponse])
def search_experiments(
    body: SearchExperimentsRequest, ctx: CurrentUser, svc: ExperimentsSvc
) -> list[ExperimentResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        ExperimentResponse.model_validate(item)
        for item in svc.search(ctx.user_id, ctx.organization_id, body.model_dump())
    ]


@router.post("/export")
def export_experiment(
    body: ExportExperimentRequest, ctx: CurrentUser, svc: ExperimentsSvc
) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.export_experiment(ctx.user_id, ctx.organization_id, body.experiment_id)


@router.post("/clone", response_model=ExperimentResponse)
def clone_experiment(
    body: CloneExperimentRequest, ctx: CurrentUser, svc: ExperimentsSvc
) -> ExperimentResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.clone_experiment(ctx.user_id, ctx.organization_id, body.experiment_id, body.name)
    return ExperimentResponse.model_validate(row)


@router.post("/compare")
def compare_runs(body: CompareRunsRequest, ctx: CurrentUser, svc: ExperimentsSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    comparison = svc.compare_runs(ctx.user_id, ctx.organization_id, body.run_ids, body.name)
    return {
        "id": str(comparison.id),
        "name": comparison.name,
        "result": comparison.result_json,
        "run_ids": comparison.run_ids_json,
    }


@router.post("/favorite", response_model=RunResponse)
def favorite_run(body: FavoriteRequest, ctx: CurrentUser, svc: ExperimentsSvc) -> RunResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    run = svc.favorite_run(ctx.user_id, ctx.organization_id, body.run_id)
    return RunResponse.model_validate(run)


@router.post("/archive")
def archive(body: ArchiveRequest, ctx: CurrentUser, svc: ExperimentsSvc) -> dict[str, str]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.archive(
        ctx.user_id,
        ctx.organization_id,
        experiment_id=body.experiment_id,
        run_id=body.run_id,
    )


def build_experiments_router() -> APIRouter:
    return router

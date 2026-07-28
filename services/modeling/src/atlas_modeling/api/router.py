"""Training HTTP API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from atlas_modeling.api.deps import ModelingSvc
from atlas_modeling.application.schemas import (
    ApproveTrainingRequest,
    ExportTrainingRequest,
    JobResponse,
    ModelResponse,
    RejectTrainingRequest,
    RunTrainingRequest,
    RunTrainingResponse,
    SearchTrainingRequest,
)

router = APIRouter(prefix="/training", tags=["training"])


def _enqueue_celery(job_id: UUID, redis_url: str) -> str:
    from celery import Celery

    app = Celery("atlas", broker=redis_url, backend=redis_url)
    result = app.send_task("atlas.worker.training", args=[str(job_id)])
    return str(result.id)


@router.post("/run/{feature_set_id}", response_model=RunTrainingResponse, status_code=202)
def run_training(
    feature_set_id: UUID,
    request: Request,
    ctx: CurrentUser,
    svc: ModelingSvc,
    body: RunTrainingRequest | None = None,
) -> RunTrainingResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    job = svc.enqueue(ctx.user_id, ctx.organization_id, feature_set_id, (body or RunTrainingRequest()).config)

    settings = getattr(request.app.state, "settings", None)
    if getattr(settings, "atlas_env", "") == "testing":
        svc.repo.session.flush()
        svc.run_job(job.id)
        return RunTrainingResponse(job_id=job.id, status=job.status)

    svc.repo.session.commit()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    try:
        _enqueue_celery(job.id, redis_url)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        svc.repo.session.commit()
        raise HTTPException(status_code=503, detail="failed to enqueue training job") from exc
    return RunTrainingResponse(job_id=job.id, status="queued")


@router.get("/", response_model=list[ModelResponse])
def list_training(ctx: CurrentUser, svc: ModelingSvc) -> list[ModelResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [ModelResponse.model_validate(m) for m in svc.list_models(ctx.user_id, ctx.organization_id)]


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(ctx: CurrentUser, svc: ModelingSvc) -> list[JobResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [JobResponse.model_validate(j) for j in svc.list_jobs(ctx.user_id, ctx.organization_id)]


@router.get("/jobs/{id}", response_model=JobResponse)
def get_job(id: UUID, ctx: CurrentUser, svc: ModelingSvc) -> JobResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.get_job(ctx.user_id, ctx.organization_id, id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse.model_validate(row)


@router.get("/models", response_model=list[ModelResponse])
def list_models(ctx: CurrentUser, svc: ModelingSvc) -> list[ModelResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [ModelResponse.model_validate(m) for m in svc.list_models(ctx.user_id, ctx.organization_id)]


@router.get("/models/{id}", response_model=ModelResponse)
def get_model(id: UUID, ctx: CurrentUser, svc: ModelingSvc) -> ModelResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.get_model(ctx.user_id, ctx.organization_id, id)
    if row is None:
        raise HTTPException(status_code=404, detail="model not found")
    return ModelResponse.model_validate(row)


@router.get("/report/{id}")
def get_report(id: UUID, ctx: CurrentUser, svc: ModelingSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.get_report(ctx.user_id, ctx.organization_id, id)


@router.post("/approve")
def approve(body: ApproveTrainingRequest, ctx: CurrentUser, svc: ModelingSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    model = svc.approve(ctx.user_id, ctx.organization_id, body.job_id, body.note)
    return {"job_id": str(body.job_id), "status": "completed", "model_id": str(model.id)}


@router.post("/reject")
def reject(body: RejectTrainingRequest, ctx: CurrentUser, svc: ModelingSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    job = svc.reject(ctx.user_id, ctx.organization_id, body.job_id, body.reason)
    return {"job_id": str(body.job_id), "status": job.status}


@router.post("/export")
def export_training(body: ExportTrainingRequest, ctx: CurrentUser, svc: ModelingSvc) -> JSONResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return JSONResponse(svc.export(ctx.user_id, ctx.organization_id, body.job_id))


@router.post("/search", response_model=list[ModelResponse])
def search_training(
    body: SearchTrainingRequest, ctx: CurrentUser, svc: ModelingSvc
) -> list[ModelResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        ModelResponse.model_validate(m)
        for m in svc.search(ctx.user_id, ctx.organization_id, body.query, body.limit)
    ]


def build_modeling_router() -> APIRouter:
    return router

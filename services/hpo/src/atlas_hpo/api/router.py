"""HPO HTTP API."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from atlas_hpo.api.deps import HpoSvc
from atlas_hpo.application.schemas import (
    ApproveHpoRequest,
    ExportHpoRequest,
    JobResponse,
    RejectHpoRequest,
    RunHpoRequest,
    RunHpoResponse,
    SearchHpoRequest,
    StudyResponse,
)

router = APIRouter(prefix="/hpo", tags=["hpo"])


def _enqueue_celery(job_id: UUID, redis_url: str) -> str:
    from celery import Celery

    app = Celery("atlas", broker=redis_url, backend=redis_url)
    result = app.send_task("atlas.worker.hpo", args=[str(job_id)])
    return str(result.id)


@router.post("/run/{training_job_id}", response_model=RunHpoResponse, status_code=202)
def run_hpo(
    training_job_id: UUID,
    request: Request,
    ctx: CurrentUser,
    svc: HpoSvc,
    body: RunHpoRequest | None = None,
) -> RunHpoResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    payload = (body or RunHpoRequest()).model_dump()
    job = svc.enqueue(ctx.user_id, ctx.organization_id, training_job_id, payload)

    settings = getattr(request.app.state, "settings", None)
    if getattr(settings, "atlas_env", "") == "testing":
        svc.repo.session.flush()
        study = svc.run_job(job.id)
        return RunHpoResponse(job_id=job.id, status=study.status)

    svc.repo.session.commit()
    redis_url = getattr(settings, "redis_url", "redis://localhost:6379/0")
    try:
        _enqueue_celery(job.id, redis_url)
    except Exception as exc:
        job.status = "failed"
        job.error_message = str(exc)[:2000]
        svc.repo.session.commit()
        raise HTTPException(status_code=503, detail="failed to enqueue optimization job") from exc
    return RunHpoResponse(job_id=job.id, status="queued")


@router.get("/", response_model=list[StudyResponse])
def list_hpo(ctx: CurrentUser, svc: HpoSvc) -> list[StudyResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [StudyResponse.model_validate(item) for item in svc.list_studies(ctx.user_id, ctx.organization_id)]


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(ctx: CurrentUser, svc: HpoSvc) -> list[JobResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [JobResponse.model_validate(item) for item in svc.list_jobs(ctx.user_id, ctx.organization_id)]


@router.get("/jobs/{id}", response_model=JobResponse)
def get_job(id: UUID, ctx: CurrentUser, svc: HpoSvc) -> JobResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.get_job(ctx.user_id, ctx.organization_id, id)
    if row is None:
        raise HTTPException(status_code=404, detail="job not found")
    return JobResponse.model_validate(row)


@router.get("/studies", response_model=list[StudyResponse])
def list_studies(ctx: CurrentUser, svc: HpoSvc) -> list[StudyResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [StudyResponse.model_validate(item) for item in svc.list_studies(ctx.user_id, ctx.organization_id)]


@router.get("/studies/{id}", response_model=StudyResponse)
def get_study(id: UUID, ctx: CurrentUser, svc: HpoSvc) -> StudyResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.get_study(ctx.user_id, ctx.organization_id, id)
    if row is None:
        raise HTTPException(status_code=404, detail="study not found")
    return StudyResponse.model_validate(row)


@router.get("/report/{id}")
def get_report(id: UUID, ctx: CurrentUser, svc: HpoSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.get_report(ctx.user_id, ctx.organization_id, id)


@router.post("/export")
def export_hpo(body: ExportHpoRequest, ctx: CurrentUser, svc: HpoSvc) -> JSONResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return JSONResponse(svc.export(ctx.user_id, ctx.organization_id, body.study_id))


@router.post("/search", response_model=list[StudyResponse])
def search_hpo(body: SearchHpoRequest, ctx: CurrentUser, svc: HpoSvc) -> list[StudyResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [
        StudyResponse.model_validate(item)
        for item in svc.search(ctx.user_id, ctx.organization_id, body.query, body.limit)
    ]


@router.post("/approve")
def approve_hpo(body: ApproveHpoRequest, ctx: CurrentUser, svc: HpoSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    study = svc.approve(ctx.user_id, ctx.organization_id, body.study_id, body.note)
    return {"study_id": str(study.id), "status": study.status}


@router.post("/reject")
def reject_hpo(body: RejectHpoRequest, ctx: CurrentUser, svc: HpoSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    study = svc.reject(ctx.user_id, ctx.organization_id, body.study_id, body.reason)
    return {"study_id": str(study.id), "status": study.status}


def build_hpo_router() -> APIRouter:
    return router

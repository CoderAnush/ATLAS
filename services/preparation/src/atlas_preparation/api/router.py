"""Preparation HTTP API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from atlas_core.errors import NotFoundError
from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from atlas_preparation.api.deps import PrepSvc
from atlas_preparation.application.schemas import (
    ApproveRequest,
    ExportRequest,
    JobResponse,
    PreparationSummaryResponse,
    RejectRequest,
    RunPreparationRequest,
    RunPreparationResponse,
)
from atlas_preparation.domain import JobStatus

logger = logging.getLogger("atlas.preparation")

router = APIRouter(prefix="/preparation", tags=["preparation"])


def _enqueue_celery(job_id: UUID, redis_url: str) -> str:
    """Publish cleaning task to the shared Celery broker."""
    from celery import Celery

    app = Celery("atlas", broker=redis_url, backend=redis_url)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
    )
    result = app.send_task("atlas.worker.preparation", args=[str(job_id)])
    return str(result.id)


@router.post("/run/{dataset_id}", response_model=RunPreparationResponse, status_code=202)
def run_preparation(
    dataset_id: UUID,
    request: Request,
    ctx: CurrentUser,
    svc: PrepSvc,
    body: RunPreparationRequest | None = None,
) -> RunPreparationResponse:
    """Start a new cleaning analysis job for a dataset."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    strategies = body.strategies if body else {}
    job = svc.enqueue(ctx.user_id, ctx.organization_id, dataset_id, strategies)

    logger.info(
        "JobQueued",
        extra={
            "job_id": str(job.id),
            "dataset_id": str(dataset_id),
            "tenant_id": str(ctx.organization_id),
        },
    )

    settings = getattr(request.app.state, "settings", None)
    atlas_env = getattr(settings, "atlas_env", "") if settings else ""

    if atlas_env == "testing":
        svc.repo.session.flush()
        svc.run_job(job.id)
        return RunPreparationResponse(job_id=job.id, status=job.status)

    svc.repo.session.commit()

    redis_url = (
        getattr(settings, "redis_url", "redis://localhost:6379/0")
        if settings
        else "redis://localhost:6379/0"
    )
    try:
        celery_task_id = _enqueue_celery(job.id, redis_url)
        logger.info(
            "JobQueued",
            extra={"job_id": str(job.id), "celery_task_id": celery_task_id, "broker": redis_url},
        )
    except Exception as exc:
        logger.exception("Failed to enqueue cleaning job_id=%s", job.id)
        job.status = JobStatus.FAILED.value
        job.error_message = f"failed to enqueue celery task: {exc}"[:2000]
        svc.repo.session.commit()
        raise HTTPException(status_code=503, detail="failed to enqueue cleaning job") from exc

    return RunPreparationResponse(job_id=job.id, status=JobStatus.QUEUED.value)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(ctx: CurrentUser, svc: PrepSvc) -> list[JobResponse]:
    """List all cleaning jobs for the organization."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return [JobResponse.model_validate(j) for j in svc.repo.list_jobs(ctx.organization_id)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, ctx: CurrentUser, svc: PrepSvc) -> JobResponse:
    """Get a specific cleaning job."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    job = svc.repo.get_job(ctx.organization_id, job_id)
    if job is None:
        raise NotFoundError("job not found")
    return JobResponse.model_validate(job)


@router.get("/recipe/{recipe_id}")
def get_recipe(recipe_id: UUID, ctx: CurrentUser, svc: PrepSvc) -> dict[str, Any]:
    """Get recipe details including steps."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return svc.get_recipe(ctx.user_id, ctx.organization_id, recipe_id)


@router.get("/report/{report_id}")
def get_report(report_id: UUID, ctx: CurrentUser, svc: PrepSvc) -> dict[str, Any]:
    """Get report details including before/after quality."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return svc.get_report(ctx.user_id, ctx.organization_id, report_id)


@router.get("/{dataset_id}/history")
def get_history(dataset_id: UUID, ctx: CurrentUser, svc: PrepSvc) -> list[dict[str, Any]]:
    """Transformation timeline for a dataset."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.list_history(ctx.user_id, ctx.organization_id, dataset_id)


@router.get("/{dataset_id}", response_model=PreparationSummaryResponse)
def get_preparation_summary(
    dataset_id: UUID, ctx: CurrentUser, svc: PrepSvc
) -> PreparationSummaryResponse:
    """Get the latest cleaning summary for a dataset."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    summary = svc.get_summary(ctx.user_id, ctx.organization_id, dataset_id)
    return PreparationSummaryResponse(**summary)


@router.post("/approve")
def approve_cleaning(body: ApproveRequest, ctx: CurrentUser, svc: PrepSvc) -> dict[str, Any]:
    """Approve a cleaning job and apply transformations.

    Optionally provide edited_steps to modify the recipe before applying.
    Creates a new dataset version with cleaned data.
    """
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    prepared = svc.approve(ctx.user_id, ctx.organization_id, body.job_id, body.edited_steps)

    return {
        "job_id": str(body.job_id),
        "status": "completed",
        "output_dataset_id": str(prepared.output_dataset_id),
        "output_version": prepared.output_version,
        "rows": prepared.rows,
        "columns": prepared.columns,
    }


@router.post("/reject")
def reject_cleaning(body: RejectRequest, ctx: CurrentUser, svc: PrepSvc) -> dict[str, Any]:
    """Reject a cleaning job."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    job = svc.reject(ctx.user_id, ctx.organization_id, body.job_id, body.reason)

    return {
        "job_id": str(body.job_id),
        "status": job.status,
        "reason": body.reason,
    }


@router.post("/export")
def export_cleaning(body: ExportRequest, ctx: CurrentUser, svc: PrepSvc) -> JSONResponse:
    """Export cleaned dataset or recipe.

    Returns presigned URL for cleaned data and/or recipe JSON.
    """
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    result = svc.export(ctx.user_id, ctx.organization_id, body.job_id)

    return JSONResponse(result)


def build_preparation_router() -> APIRouter:
    """Factory function for including in the main app."""
    return router

"""Profiling HTTP API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from atlas_core.errors import NotFoundError
from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import JSONResponse

from atlas_profiling.api.deps import ProfilingSvc
from atlas_profiling.application.schemas import (
    JobResponse,
    ProfileSummaryResponse,
    RunProfilingResponse,
)
from atlas_profiling.domain import JobStatus

logger = logging.getLogger("atlas.profiling")

router = APIRouter(prefix="/profiling", tags=["profiling"])


def _enqueue_celery(job_id: UUID, redis_url: str) -> str:
    """Publish profiling task to the shared Celery broker (no worker package import)."""
    from celery import Celery

    app = Celery("atlas", broker=redis_url, backend=redis_url)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
    )
    result = app.send_task("atlas.worker.profiling", args=[str(job_id)])
    return str(result.id)


@router.post("/run/{dataset_id}", response_model=RunProfilingResponse, status_code=202)
def run_profiling(
    dataset_id: UUID, request: Request, ctx: CurrentUser, svc: ProfilingSvc
) -> RunProfilingResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    job = svc.enqueue(ctx.user_id, ctx.organization_id, dataset_id)
    logger.info(
        "JobCreated",
        extra={
            "job_id": str(job.id),
            "dataset_id": str(dataset_id),
            "tenant_id": str(ctx.organization_id),
        },
    )

    settings = getattr(request.app.state, "settings", None)
    atlas_env = getattr(settings, "atlas_env", "") if settings else ""

    if atlas_env == "testing":
        # Inline execution shares the request session; flush is enough.
        svc.repo.session.flush()
        svc.run_job(job.id)
        return RunProfilingResponse(job_id=job.id, status=job.status)

    # Commit before broker publish so workers can load the job row.
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
        logger.exception("Failed to enqueue profiling job_id=%s", job.id)
        job.status = JobStatus.FAILED.value
        job.error_message = f"failed to enqueue celery task: {exc}"[:2000]
        svc.repo.session.commit()
        raise HTTPException(status_code=503, detail="failed to enqueue profiling job") from exc

    return RunProfilingResponse(job_id=job.id, status=JobStatus.QUEUED.value)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(ctx: CurrentUser, svc: ProfilingSvc) -> list[JobResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [JobResponse.model_validate(j) for j in svc.repo.list_jobs(ctx.organization_id)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, ctx: CurrentUser, svc: ProfilingSvc) -> JobResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    job = svc.repo.get_job(ctx.organization_id, job_id)
    if job is None:
        raise NotFoundError("job not found")
    return JobResponse.model_validate(job)


@router.get("/{dataset_id}")
def get_profile(dataset_id: UUID, ctx: CurrentUser, svc: ProfilingSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return svc.get_profile(ctx.user_id, ctx.organization_id, dataset_id)


@router.get("/{dataset_id}/summary", response_model=ProfileSummaryResponse)
def get_summary(dataset_id: UUID, ctx: CurrentUser, svc: ProfilingSvc) -> ProfileSummaryResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.get_profile_row(ctx.user_id, ctx.organization_id, dataset_id)
    return ProfileSummaryResponse(
        dataset_id=row.dataset_id,
        dataset_version=row.dataset_version,
        rows=row.rows,
        columns=row.columns,
        problem_type=row.problem_type,
        target_column=row.target_column,
        target_confidence=row.target_confidence,
        health=row.health,
        quality_overall=row.quality_overall,
        summary=row.summary,
    )


@router.get("/{dataset_id}/quality")
def get_quality(dataset_id: UUID, ctx: CurrentUser, svc: ProfilingSvc) -> dict[str, Any]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    profile = svc.get_profile(ctx.user_id, ctx.organization_id, dataset_id)
    quality = profile.get("quality")
    return quality if isinstance(quality, dict) else {}


@router.get("/{dataset_id}/statistics")
def get_statistics(
    dataset_id: UUID,
    ctx: CurrentUser,
    svc: ProfilingSvc,
    kind: str | None = None,
    sort: str = Query("missing_pct", pattern="^(missing_pct|unique|name|variance)$"),
    q: str | None = None,
) -> list[dict[str, Any]]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    profile = svc.get_profile(ctx.user_id, ctx.organization_id, dataset_id)
    cols = list(profile.get("columns", []))
    if kind:
        cols = [c for c in cols if c.get("kind") == kind]
    if q:
        ql = q.lower()
        cols = [c for c in cols if ql in str(c.get("name", "")).lower()]
    if sort == "missing_pct":
        cols.sort(key=lambda c: c.get("missing_pct", 0), reverse=True)
    elif sort == "unique":
        cols.sort(key=lambda c: c.get("unique", 0), reverse=True)
    elif sort == "variance":
        cols.sort(
            key=lambda c: (c.get("statistics") or {}).get("variance") or 0,
            reverse=True,
        )
    else:
        cols.sort(key=lambda c: str(c.get("name", "")))
    return cols


@router.get("/{dataset_id}/visualizations")
def get_visualizations(dataset_id: UUID, ctx: CurrentUser, svc: ProfilingSvc) -> JSONResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    url, _ctype = svc.download_artifact(ctx.user_id, ctx.organization_id, dataset_id, "plotly")
    return JSONResponse({"url": url, "expires_in_seconds": 3600})


@router.get("/{dataset_id}/download")
def download_report(
    dataset_id: UUID,
    ctx: CurrentUser,
    svc: ProfilingSvc,
    format: str = Query("json", pattern="^(json|markdown|html|pdf)$"),
) -> JSONResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    url, ctype = svc.download_artifact(ctx.user_id, ctx.organization_id, dataset_id, format)
    return JSONResponse({"url": url, "content_type": ctype, "expires_in_seconds": 3600})


def build_profiling_router() -> APIRouter:
    return router

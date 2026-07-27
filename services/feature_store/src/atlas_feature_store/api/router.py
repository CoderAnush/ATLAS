"""Feature store HTTP API."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from atlas_core.errors import NotFoundError
from atlas_identity.api.deps import CurrentUser, require_org_context
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from atlas_feature_store.api.deps import FeatureSvc
from atlas_feature_store.application.schemas import (
    ApproveRequest,
    ExportRequest,
    FeatureSetResponse,
    FeatureSummaryResponse,
    JobResponse,
    RejectRequest,
    RunFeaturesRequest,
    RunFeaturesResponse,
    SearchRequest,
)
from atlas_feature_store.domain import JobStatus

logger = logging.getLogger("atlas.features")

router = APIRouter(prefix="/features", tags=["features"])


def _enqueue_celery(job_id: UUID, redis_url: str) -> str:
    """Publish feature engineering task to the shared Celery broker."""
    from celery import Celery

    app = Celery("atlas", broker=redis_url, backend=redis_url)
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
    )
    result = app.send_task("atlas.worker.features", args=[str(job_id)])
    return str(result.id)


@router.post("/run/{dataset_id}", response_model=RunFeaturesResponse, status_code=202)
def run_features(
    dataset_id: UUID,
    request: Request,
    ctx: CurrentUser,
    svc: FeatureSvc,
    body: RunFeaturesRequest | None = None,
) -> RunFeaturesResponse:
    """Start a new feature engineering job for a dataset."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    config = body.config if body else {}
    job = svc.enqueue(ctx.user_id, ctx.organization_id, dataset_id, config)

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
        return RunFeaturesResponse(job_id=job.id, status=job.status)

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
        logger.exception("Failed to enqueue feature job_id=%s", job.id)
        job.status = JobStatus.FAILED.value
        job.error_message = f"failed to enqueue celery task: {exc}"[:2000]
        svc.repo.session.commit()
        raise HTTPException(status_code=503, detail="failed to enqueue feature job") from exc

    return RunFeaturesResponse(job_id=job.id, status=JobStatus.QUEUED.value)


@router.get("/jobs", response_model=list[JobResponse])
def list_jobs(ctx: CurrentUser, svc: FeatureSvc) -> list[JobResponse]:
    """List all feature engineering jobs for the organization."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return [JobResponse.model_validate(j) for j in svc.list_jobs(ctx.user_id, ctx.organization_id)]


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: UUID, ctx: CurrentUser, svc: FeatureSvc) -> JobResponse:
    """Get a specific feature engineering job."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    job = svc.get_job(ctx.user_id, ctx.organization_id, job_id)
    if job is None:
        raise NotFoundError("job not found")
    return JobResponse.model_validate(job)


@router.get("/", response_model=list[FeatureSetResponse])
def list_feature_sets(ctx: CurrentUser, svc: FeatureSvc) -> list[FeatureSetResponse]:
    """List feature sets (alias for backward compatibility)."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return [
        FeatureSetResponse.model_validate(fs)
        for fs in svc.list_feature_sets(ctx.user_id, ctx.organization_id)
    ]


@router.get("/dataset/{dataset_id}", response_model=FeatureSummaryResponse)
def get_dataset_summary(
    dataset_id: UUID, ctx: CurrentUser, svc: FeatureSvc
) -> FeatureSummaryResponse:
    """Get the latest feature engineering summary for a dataset."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    summary = svc.get_summary(ctx.user_id, ctx.organization_id, dataset_id)
    return FeatureSummaryResponse(**summary)


@router.get("/{id}", response_model=FeatureSetResponse)
def get_feature_set(id: UUID, ctx: CurrentUser, svc: FeatureSvc) -> FeatureSetResponse:
    """Get a specific feature set."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    fs = svc.get_feature_set(ctx.user_id, ctx.organization_id, id)
    if fs is None:
        raise NotFoundError("feature set not found")
    return FeatureSetResponse.model_validate(fs)


@router.get("/report/{id}")
def get_report(id: UUID, ctx: CurrentUser, svc: FeatureSvc) -> dict[str, Any]:
    """Get report details for a feature set."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return svc.get_report(ctx.user_id, ctx.organization_id, id)


@router.get("/lineage/{id}")
def get_lineage(id: UUID, ctx: CurrentUser, svc: FeatureSvc) -> list[dict[str, Any]]:
    """Get lineage for a feature set."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    return svc.get_lineage(ctx.user_id, ctx.organization_id, id)


@router.post("/approve")
def approve_features(body: ApproveRequest, ctx: CurrentUser, svc: FeatureSvc) -> dict[str, Any]:
    """Approve a feature engineering job and apply transformations.

    Optionally provide edited_steps or selected_features to modify the pipeline.
    Creates a new dataset version with feature matrix.
    """
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    feature_set = svc.approve(
        ctx.user_id,
        ctx.organization_id,
        body.job_id,
        body.edited_steps,
        body.selected_features,
    )

    return {
        "job_id": str(body.job_id),
        "status": "completed",
        "feature_set_id": str(feature_set.id),
        "output_version": feature_set.output_dataset_version,
        "rows": feature_set.rows,
        "columns": feature_set.columns,
    }


@router.post("/reject")
def reject_features(body: RejectRequest, ctx: CurrentUser, svc: FeatureSvc) -> dict[str, Any]:
    """Reject a feature engineering job."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    job = svc.reject(ctx.user_id, ctx.organization_id, body.job_id, body.reason)

    return {
        "job_id": str(body.job_id),
        "status": job.status,
        "reason": body.reason,
    }


@router.post("/export")
def export_features(body: ExportRequest, ctx: CurrentUser, svc: FeatureSvc) -> JSONResponse:
    """Export feature matrix or pipeline.

    Returns presigned URL for feature matrix and/or pipeline JSON.
    """
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    result = svc.export(ctx.user_id, ctx.organization_id, body.job_id)

    return JSONResponse(result)


@router.post("/search")
def search_features(
    body: SearchRequest, ctx: CurrentUser, svc: FeatureSvc
) -> list[FeatureSetResponse]:
    """Search feature sets by query and optional tags."""
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None

    results = svc.search(ctx.user_id, ctx.organization_id, body.query, body.tags, body.limit)

    return [FeatureSetResponse.model_validate(fs) for fs in results]


def build_feature_store_router() -> APIRouter:
    """Factory function for including in the main app."""
    return router

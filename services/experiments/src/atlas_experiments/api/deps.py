"""FastAPI dependencies for experiments."""

from __future__ import annotations

from typing import Annotated

from atlas_identity.api.deps import DbSession
from atlas_identity.infrastructure.repository import IdentityRepository
from fastapi import Depends, Request

from atlas_experiments.application.service import ExperimentsService
from atlas_experiments.infrastructure.mlflow import build_experiment_tracker
from atlas_experiments.infrastructure.repository import ExperimentRepository


def get_experiments_service(request: Request, session: DbSession) -> ExperimentsService:
    container = request.app.state.container
    settings = request.app.state.settings
    tracker = getattr(container, "experiment_tracker", None)
    if tracker is None:
        tracker = build_experiment_tracker(getattr(settings, "mlflow_tracking_uri", None))
    return ExperimentsService(
        ExperimentRepository(session),
        IdentityRepository(session),
        container.storage,
        tracker,
        bucket=settings.minio_bucket,
    )


ExperimentsSvc = Annotated[ExperimentsService, Depends(get_experiments_service)]

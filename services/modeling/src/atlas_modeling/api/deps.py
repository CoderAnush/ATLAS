"""Modeling FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_experiments.application.service import ExperimentsService
from atlas_experiments.infrastructure.mlflow import build_experiment_tracker
from atlas_experiments.infrastructure.repository import ExperimentRepository
from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
from atlas_identity.api.deps import get_db_session
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_profiling.infrastructure.repository import ProfilingRepository
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from atlas_modeling.application.service import ModelingService
from atlas_modeling.infrastructure.repository import ModelingRepository


def get_modeling_service(
    request: Request, session: Session = Depends(get_db_session)
) -> Generator[ModelingService, None, None]:
    settings = request.app.state.container.settings
    container = request.app.state.container
    tracker = getattr(container, "experiment_tracker", None) or build_experiment_tracker(
        getattr(settings, "mlflow_tracking_uri", None)
    )
    experiments = ExperimentsService(
        ExperimentRepository(session),
        IdentityRepository(session),
        container.storage,
        tracker,
        bucket=settings.minio_bucket,
    )
    yield ModelingService(
        ModelingRepository(session),
        CatalogRepository(session),
        FeatureStoreRepository(session),
        IdentityRepository(session),
        ProfilingRepository(session),
        container.storage,
        bucket=settings.minio_bucket,
        experiments=experiments,
    )


ModelingSvc = Annotated[ModelingService, Depends(get_modeling_service)]

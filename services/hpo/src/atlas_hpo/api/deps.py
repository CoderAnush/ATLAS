"""FastAPI dependencies for HPO."""

from __future__ import annotations

from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_experiments.application.service import ExperimentsService
from atlas_experiments.infrastructure.mlflow import build_experiment_tracker
from atlas_experiments.infrastructure.repository import ExperimentRepository
from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
from atlas_identity.api.deps import DbSession
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_modeling.infrastructure.repository import ModelingRepository
from atlas_profiling.infrastructure.repository import ProfilingRepository
from fastapi import Depends, Request

from atlas_hpo.application.service import HpoService
from atlas_hpo.infrastructure.repository import HpoRepository


def get_hpo_service(request: Request, session: DbSession) -> HpoService:
    container = request.app.state.container
    settings = request.app.state.settings
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
    return HpoService(
        HpoRepository(session),
        ModelingRepository(session),
        CatalogRepository(session),
        FeatureStoreRepository(session),
        IdentityRepository(session),
        ProfilingRepository(session),
        container.storage,
        bucket=settings.minio_bucket,
        experiments=experiments,
    )


HpoSvc = Annotated[HpoService, Depends(get_hpo_service)]

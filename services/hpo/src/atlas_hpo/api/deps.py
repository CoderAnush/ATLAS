"""FastAPI dependencies for HPO."""

from __future__ import annotations

from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
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
    return HpoService(
        HpoRepository(session),
        ModelingRepository(session),
        CatalogRepository(session),
        FeatureStoreRepository(session),
        IdentityRepository(session),
        ProfilingRepository(session),
        container.storage,
        bucket=settings.minio_bucket,
    )


HpoSvc = Annotated[HpoService, Depends(get_hpo_service)]

"""Modeling FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
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
    yield ModelingService(
        ModelingRepository(session),
        CatalogRepository(session),
        FeatureStoreRepository(session),
        IdentityRepository(session),
        ProfilingRepository(session),
        request.app.state.container.storage,
        bucket=settings.minio_bucket,
    )


ModelingSvc = Annotated[ModelingService, Depends(get_modeling_service)]

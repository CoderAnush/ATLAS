"""Preparation FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_identity.api.deps import get_db_session
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_profiling.infrastructure.repository import ProfilingRepository
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from atlas_preparation.application.service import PreparationService
from atlas_preparation.infrastructure.repository import PreparationRepository


def get_preparation_service(
    request: Request, session: Session = Depends(get_db_session)
) -> Generator[PreparationService, None, None]:
    settings = request.app.state.container.settings
    yield PreparationService(
        PreparationRepository(session),
        CatalogRepository(session),
        IdentityRepository(session),
        ProfilingRepository(session),
        request.app.state.container.storage,
        bucket=settings.minio_bucket,
    )


PrepSvc = Annotated[PreparationService, Depends(get_preparation_service)]

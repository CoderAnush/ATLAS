"""Profiling FastAPI deps."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_identity.api.deps import get_db_session
from atlas_identity.infrastructure.repository import IdentityRepository
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from atlas_profiling.application.service import ProfilingService
from atlas_profiling.infrastructure.repository import ProfilingRepository


def get_profiling_service(
    request: Request, session: Session = Depends(get_db_session)
) -> Generator[ProfilingService, None, None]:
    settings = request.app.state.container.settings
    yield ProfilingService(
        ProfilingRepository(session),
        CatalogRepository(session),
        IdentityRepository(session),
        request.app.state.container.storage,
        bucket=settings.minio_bucket,
    )


ProfilingSvc = Annotated[ProfilingService, Depends(get_profiling_service)]

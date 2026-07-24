"""FastAPI dependency wiring for catalog."""

from __future__ import annotations

from collections.abc import Generator
from typing import Annotated

from atlas_identity.api.deps import get_db_session
from atlas_identity.infrastructure.repository import IdentityRepository
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from atlas_catalog.application.service import CatalogService
from atlas_catalog.infrastructure.repository import CatalogRepository


def get_catalog_service(
    request: Request, session: Session = Depends(get_db_session)
) -> Generator[CatalogService, None, None]:
    settings = request.app.state.container.settings
    storage = request.app.state.container.storage
    yield CatalogService(
        CatalogRepository(session),
        IdentityRepository(session),
        storage,
        bucket=settings.minio_bucket,
        max_upload_bytes=settings.atlas_max_upload_bytes,
    )


CatalogSvc = Annotated[CatalogService, Depends(get_catalog_service)]

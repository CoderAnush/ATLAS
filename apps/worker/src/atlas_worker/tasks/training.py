"""Celery task: run training job."""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from atlas_core.errors import NotFoundError

from atlas_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    user = os.getenv("POSTGRES_USER", "atlas")
    password = os.getenv("POSTGRES_PASSWORD", "atlas")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "atlas")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


@celery_app.task(name="atlas.worker.training", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def run_training_job(self: Any, job_id: str) -> dict[str, str]:
    from atlas_catalog.infrastructure.repository import CatalogRepository
    from atlas_db.session import create_engine_from_url, create_session_factory
    from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
    from atlas_identity.infrastructure.repository import IdentityRepository
    from atlas_modeling.application.service import ModelingService
    from atlas_modeling.infrastructure.repository import ModelingRepository
    from atlas_profiling.infrastructure.repository import ProfilingRepository
    from atlas_storage.minio_client import MinioObjectStorage
    from minio import Minio

    engine = create_engine_from_url(_database_url())
    factory = create_session_factory(engine)
    session = factory()
    try:
        endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        access = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        secret = os.getenv("MINIO_SECRET_KEY", "minioadmin")
        secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        bucket = os.getenv("MINIO_BUCKET", "atlas")
        client = Minio(endpoint, access_key=access, secret_key=secret, secure=secure)
        storage = MinioObjectStorage(client)
        svc = ModelingService(
            ModelingRepository(session),
            CatalogRepository(session),
            FeatureStoreRepository(session),
            IdentityRepository(session),
            ProfilingRepository(session),
            storage,
            bucket=bucket,
        )
        svc.run_job(uuid.UUID(job_id))
        session.commit()
        return {"status": "awaiting_approval", "job_id": job_id}
    except NotFoundError as exc:
        session.rollback()
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
        raise
    finally:
        session.close()
        engine.dispose()

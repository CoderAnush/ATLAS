"""Celery task: run feature engineering job."""

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


def _persist_failed(job_id: str, message: str) -> None:
    from atlas_db.session import create_engine_from_url, create_session_factory
    from atlas_feature_store.domain import JobStatus
    from atlas_feature_store.infrastructure.repository import (
        FeatureStoreRepository,
        utcnow,
    )

    engine = create_engine_from_url(_database_url())
    factory = create_session_factory(engine)
    session = factory()
    try:
        repo = FeatureStoreRepository(session)
        job = repo.get_job_any(uuid.UUID(job_id))
        if job is None:
            return
        if job.status in {JobStatus.COMPLETED.value, JobStatus.REJECTED.value}:
            return
        job.status = JobStatus.FAILED.value
        job.error_message = message[:2000]
        job.completed_at = utcnow()
        session.commit()
        logger.info("FeatureGenerationFailed job_id=%s status=failed", job_id)
    except Exception:
        session.rollback()
        logger.exception("unable to persist FAILED status job_id=%s", job_id)
    finally:
        session.close()
        engine.dispose()


@celery_app.task(name="atlas.worker.features", bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def run_feature_engineering_job(self: Any, job_id: str) -> dict[str, str]:
    """Load job, generate feature engineering pipeline, await human approval."""
    from atlas_catalog.infrastructure.repository import CatalogRepository
    from atlas_db.session import create_engine_from_url, create_session_factory
    from atlas_feature_store.application.service import FeatureStoreService
    from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
    from atlas_identity.infrastructure.repository import IdentityRepository
    from atlas_profiling.infrastructure.repository import ProfilingRepository
    from atlas_storage.minio_client import MinioObjectStorage
    from minio import Minio

    logger.info("WorkerPickedUp job_id=%s", job_id)

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
        svc = FeatureStoreService(
            FeatureStoreRepository(session),
            CatalogRepository(session),
            IdentityRepository(session),
            ProfilingRepository(session),
            storage,
            bucket=bucket,
        )
        logger.info("FeatureGenerationStarted job_id=%s", job_id)
        svc.run_job(uuid.UUID(job_id))
        session.commit()
        logger.info("FeaturePipelineReady job_id=%s", job_id)
        return {"status": "awaiting_approval", "job_id": job_id}
    except NotFoundError as exc:
        session.rollback()
        if self.request.retries < self.max_retries:
            logger.warning(
                "feature job not visible yet job_id=%s retry=%s",
                job_id,
                self.request.retries + 1,
            )
            raise self.retry(exc=exc, countdown=2**self.request.retries) from exc
        logger.exception("feature job failed job_id=%s", job_id)
        _persist_failed(job_id, str(exc))
        raise
    except Exception as exc:
        session.rollback()
        logger.exception("feature job failed job_id=%s", job_id)
        _persist_failed(job_id, str(exc))
        raise
    finally:
        session.close()
        engine.dispose()

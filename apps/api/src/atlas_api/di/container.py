"""Lightweight dependency container for infrastructure adapters."""

from __future__ import annotations

from dataclasses import dataclass

from atlas_db.session import create_engine_from_url, create_session_factory
from atlas_experiments.application.ports import ExperimentTracker, NoOpExperimentTracker
from atlas_experiments.infrastructure.mlflow import build_experiment_tracker
from atlas_storage.minio_client import MinioObjectStorage
from minio import Minio
from redis import Redis
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from atlas_api.config import Settings


@dataclass
class AppContainer:
    """Holds shared infrastructure clients for the API process."""

    settings: Settings
    engine: Engine
    session_factory: sessionmaker[Session]
    redis: Redis[str]
    storage: MinioObjectStorage
    minio_client: Minio
    experiment_tracker: ExperimentTracker


def build_container(settings: Settings) -> AppContainer:
    """Construct infrastructure clients from settings."""
    engine = create_engine_from_url(settings.sqlalchemy_database_url)
    session_factory = create_session_factory(engine)
    redis: Redis[str] = Redis.from_url(settings.redis_url, decode_responses=True)
    minio_client = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    storage = MinioObjectStorage(minio_client)
    experiment_tracker: ExperimentTracker
    if settings.atlas_env == "testing":
        experiment_tracker = NoOpExperimentTracker()
    else:
        experiment_tracker = build_experiment_tracker(settings.mlflow_tracking_uri)
    return AppContainer(
        settings=settings,
        engine=engine,
        session_factory=session_factory,
        redis=redis,
        storage=storage,
        minio_client=minio_client,
        experiment_tracker=experiment_tracker,
    )

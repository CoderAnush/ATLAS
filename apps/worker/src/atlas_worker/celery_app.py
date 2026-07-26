"""Celery application for ATLAS background work."""

from __future__ import annotations

from atlas_telemetry.logging import configure_logging
from celery import Celery
from celery.signals import setup_logging as celery_setup_logging
from celery.signals import worker_ready, worker_shutting_down

from atlas_worker.config import get_worker_settings

settings = get_worker_settings()

celery_app = Celery(
    "atlas",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "atlas_worker.tasks.heartbeat",
        "atlas_worker.tasks.profiling",
        "atlas_worker.tasks.preparation",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_always_eager=settings.celery_task_always_eager,
    worker_hijack_root_logger=False,
)


@celery_setup_logging.connect  # type: ignore[untyped-decorator]
def _configure_celery_logging(**_kwargs: object) -> None:
    configure_logging(settings.atlas_log_level, json_logs=settings.atlas_json_logs)


@worker_ready.connect  # type: ignore[untyped-decorator]
def _on_ready(**_kwargs: object) -> None:
    import logging

    logging.getLogger(__name__).info("ATLAS worker ready")


@worker_shutting_down.connect  # type: ignore[untyped-decorator]
def _on_shutdown(**_kwargs: object) -> None:
    import logging

    logging.getLogger(__name__).info("ATLAS worker shutting down gracefully")

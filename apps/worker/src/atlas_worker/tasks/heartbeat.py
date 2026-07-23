"""Heartbeat task used to verify worker health."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from atlas_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name="atlas.worker.heartbeat")  # type: ignore[untyped-decorator]
def heartbeat() -> dict[str, str]:
    """Return a simple heartbeat payload."""
    payload = {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
        "service": "atlas-worker",
    }
    logger.info("heartbeat status=%s", payload["status"])
    return payload

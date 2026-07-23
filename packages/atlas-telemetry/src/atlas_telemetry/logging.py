"""Structured application logging configuration."""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from atlas_telemetry.request_context import get_request_id


class JsonFormatter(logging.Formatter):
    """Render log records as newline-delimited JSON."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize an individual log record."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if request_id := get_request_id():
            payload["request_id"] = request_id
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", json_logs: bool = True) -> None:
    """Configure root logging with either JSON or human-readable output."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        JsonFormatter()
        if json_logs
        else logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logging.basicConfig(level=level.upper(), handlers=[handler], force=True)

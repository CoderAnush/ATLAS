"""MLflow tracking client abstraction (connection only in Phase 1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MLflowConfig:
    """Connection settings for the MLflow tracking server."""

    tracking_uri: str


class MLflowClient:
    """Thin wrapper around the MLflow tracking URI.

    Experiment creation and logging are intentionally deferred to later phases.
    """

    def __init__(self, config: MLflowConfig) -> None:
        self._config = config

    @property
    def tracking_uri(self) -> str:
        """Return the configured tracking URI."""
        return self._config.tracking_uri

"""MLflow-backed ExperimentTracker implementation."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from atlas_experiments.application.ports import (
    ExperimentTracker,
    NoOpExperimentTracker,
    TrackerLogRequest,
    TrackerRunHandle,
)

logger = logging.getLogger("atlas.experiments.mlflow")


class MLflowExperimentTracker:
    """Adapter that talks to MLflow. Callers must only use ExperimentTracker."""

    def __init__(self, tracking_uri: str) -> None:
        self.tracking_uri = tracking_uri
        self._enabled = True
        self._fallback: NoOpExperimentTracker | None = None
        self._mlflow: Any = None
        try:
            import mlflow

            mlflow.set_tracking_uri(tracking_uri)
            self._mlflow = mlflow
        except Exception as exc:  # pragma: no cover - optional runtime
            logger.warning("MLflow unavailable, falling back to NoOp: %s", exc)
            self._enabled = False
            self._fallback = NoOpExperimentTracker()

    def start_run(self, request: TrackerLogRequest) -> TrackerRunHandle:
        if not self._enabled or self._mlflow is None:
            assert self._fallback is not None
            return self._fallback.start_run(request)
        try:
            self._mlflow.set_experiment(request.experiment_name)
            active = self._mlflow.start_run(run_name=request.run_name)
            run_id = active.info.run_id
            if request.params:
                self._mlflow.log_params(_stringify_params(request.params))
            if request.metrics:
                self._mlflow.log_metrics(request.metrics)
            if request.tags:
                self._mlflow.set_tags(request.tags)
            for name, payload in request.artifacts.items():
                self.log_artifact(run_id, name, payload)
            return TrackerRunHandle(
                run_id=run_id,
                experiment_id=str(active.info.experiment_id),
            )
        except Exception as exc:
            logger.warning("MLflow start_run failed: %s", exc)
            return TrackerRunHandle(run_id=f"local-{request.run_name}")

    def log_metrics(self, run_id: str, metrics: dict[str, float], *, step: int = 0) -> None:
        if not self._enabled or self._mlflow is None:
            return
        try:
            with self._mlflow.start_run(run_id=run_id):
                self._mlflow.log_metrics(metrics, step=step)
        except Exception as exc:
            logger.warning("MLflow log_metrics failed: %s", exc)

    def log_params(self, run_id: str, params: dict[str, Any]) -> None:
        if not self._enabled or self._mlflow is None:
            return
        try:
            with self._mlflow.start_run(run_id=run_id):
                self._mlflow.log_params(_stringify_params(params))
        except Exception as exc:
            logger.warning("MLflow log_params failed: %s", exc)

    def log_artifact(self, run_id: str, name: str, payload: bytes) -> None:
        if not self._enabled or self._mlflow is None:
            return
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / name
                path.write_bytes(payload)
                with self._mlflow.start_run(run_id=run_id):
                    self._mlflow.log_artifact(str(path))
        except Exception as exc:
            logger.warning("MLflow log_artifact failed: %s", exc)

    def end_run(self, run_id: str, *, status: str = "FINISHED") -> None:
        if not self._enabled or self._mlflow is None:
            return
        try:
            self._mlflow.end_run(status=status)
        except Exception as exc:
            logger.warning("MLflow end_run failed: %s", exc)


def build_experiment_tracker(tracking_uri: str | None) -> ExperimentTracker:
    if not tracking_uri:
        return NoOpExperimentTracker()
    return MLflowExperimentTracker(tracking_uri)


def _stringify_params(params: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, value in params.items():
        out[str(key)[:250]] = str(value)[:500]
    return out


__all__ = ["MLflowExperimentTracker", "build_experiment_tracker"]

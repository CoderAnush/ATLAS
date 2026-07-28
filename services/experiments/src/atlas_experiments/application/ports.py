"""Experiment tracker port — MLflow is an implementation detail."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class TrackerRunHandle:
    run_id: str
    experiment_id: str | None = None


@dataclass
class TrackerLogRequest:
    experiment_name: str
    run_name: str
    params: dict[str, Any] = field(default_factory=dict)
    metrics: dict[str, float] = field(default_factory=dict)
    tags: dict[str, str] = field(default_factory=dict)
    artifacts: dict[str, bytes] = field(default_factory=dict)


class ExperimentTracker(Protocol):
    """Port for external experiment backends (MLflow today, swappable later)."""

    def start_run(self, request: TrackerLogRequest) -> TrackerRunHandle: ...

    def log_metrics(self, run_id: str, metrics: dict[str, float], *, step: int = 0) -> None: ...

    def log_params(self, run_id: str, params: dict[str, Any]) -> None: ...

    def log_artifact(self, run_id: str, name: str, payload: bytes) -> None: ...

    def end_run(self, run_id: str, *, status: str = "FINISHED") -> None: ...


class NoOpExperimentTracker:
    """Tracker used when MLflow is unavailable or disabled."""

    def start_run(self, request: TrackerLogRequest) -> TrackerRunHandle:
        return TrackerRunHandle(run_id=f"noop-{request.run_name}", experiment_id=None)

    def log_metrics(self, run_id: str, metrics: dict[str, float], *, step: int = 0) -> None:
        return None

    def log_params(self, run_id: str, params: dict[str, Any]) -> None:
        return None

    def log_artifact(self, run_id: str, name: str, payload: bytes) -> None:
        return None

    def end_run(self, run_id: str, *, status: str = "FINISHED") -> None:
        return None

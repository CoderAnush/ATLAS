"""Domain enums for the experiments bounded context."""

from __future__ import annotations

from enum import StrEnum


class ExperimentStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"


class RunSource(StrEnum):
    TRAINING = "training"
    HPO = "hpo"
    MANUAL = "manual"
    CLONE = "clone"


class ArtifactKind(StrEnum):
    MODEL = "model"
    METRICS_JSON = "metrics_json"
    TRAINING_REPORT = "training_report"
    TRAINING_CONFIG = "training_config"
    FEATURE_SCHEMA = "feature_schema"
    PIPELINE_JSON = "pipeline_json"
    CONFUSION_MATRIX = "confusion_matrix"
    ROC = "roc"
    PRECISION_RECALL = "precision_recall"
    LOGS = "logs"
    REPRODUCIBILITY = "reproducibility"
    OTHER = "other"


__all__ = [
    "ArtifactKind",
    "ExperimentStatus",
    "RunSource",
    "RunStatus",
]

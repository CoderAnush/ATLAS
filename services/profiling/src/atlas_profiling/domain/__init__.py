"""Profiling domain enums and value objects."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class DatasetHealth(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    CRITICAL = "critical"


class ProblemType(StrEnum):
    BINARY_CLASSIFICATION = "binary_classification"
    MULTICLASS_CLASSIFICATION = "multiclass_classification"
    REGRESSION = "regression"
    CLUSTERING_CANDIDATE = "clustering_candidate"
    TIME_SERIES = "time_series"
    RECOMMENDATION = "recommendation"
    ANOMALY_DETECTION_CANDIDATE = "anomaly_detection_candidate"
    UNKNOWN = "unknown"


class ColumnKind(StrEnum):
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATETIME = "datetime"
    MIXED = "mixed"
    CONSTANT = "constant"
    ID = "id"


TARGET_NAME_HINTS = frozenset(
    {
        "target",
        "label",
        "class",
        "output",
        "y",
        "price",
        "salary",
        "survived",
        "default",
        "loan_status",
        "churn",
        "outcome",
        "response",
        "is_fraud",
        "fraud",
        "status",
        "rating",
        "score",
    }
)

ID_NAME_HINTS = frozenset(
    {
        "id",
        "uuid",
        "guid",
        "customer_id",
        "user_id",
        "account_id",
        "transaction_id",
        "order_id",
        "index",
        "pk",
    }
)

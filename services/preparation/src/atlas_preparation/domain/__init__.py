"""Preparation domain enums and value objects."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class PlanStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


class StepKind(StrEnum):
    DROP_COLUMN = "drop_column"
    DROP_ROWS_MISSING = "drop_rows_missing"
    IMPUTE_MEAN = "impute_mean"
    IMPUTE_MEDIAN = "impute_median"
    IMPUTE_MODE = "impute_mode"
    IMPUTE_CONSTANT = "impute_constant"
    IMPUTE_FFILL = "impute_ffill"
    IMPUTE_BFILL = "impute_bfill"
    IMPUTE_INTERPOLATE = "impute_interpolate"
    IMPUTE_KNN = "impute_knn"
    IMPUTE_ITERATIVE = "impute_iterative"
    DROP_DUPLICATES = "drop_duplicates"
    DROP_NEAR_DUPLICATES = "drop_near_duplicates"
    DROP_DUPLICATE_IDS = "drop_duplicate_ids"
    OUTLIER_REMOVE = "outlier_remove"
    OUTLIER_CAP = "outlier_cap"
    OUTLIER_WINSORIZE = "outlier_winsorize"
    CATEGORICAL_NORMALIZE = "categorical_normalize"
    CATEGORICAL_MERGE = "categorical_merge"
    CATEGORICAL_UNKNOWN = "categorical_unknown"
    NUMERIC_CLIP = "numeric_clip"
    NUMERIC_CLEAN_INF = "numeric_clean_inf"
    NUMERIC_IMPOSSIBLE = "numeric_impossible"
    DATETIME_PARSE = "datetime_parse"
    TEXT_NORMALIZE = "text_normalize"
    CAST_DTYPE = "cast_dtype"
    RENAME_COLUMN = "rename_column"
    REORDER_COLUMNS = "reorder_columns"
    DROP_CONSTANT = "drop_constant"
    DROP_EMPTY = "drop_empty"


class OutlierMethod(StrEnum):
    IQR = "iqr"
    ZSCORE = "zscore"
    MODIFIED_Z = "modified_z"
    ISOLATION_FOREST = "isolation_forest"
    LOF = "lof"
    DBSCAN = "dbscan"


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

ENGLISH_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "by",
        "from",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "shall",
        "can",
        "this",
        "that",
        "these",
        "those",
        "it",
        "its",
    }
)

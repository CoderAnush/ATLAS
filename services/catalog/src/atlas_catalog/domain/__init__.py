"""Catalog domain: statuses, formats, validation rules."""

from __future__ import annotations

from enum import StrEnum

from atlas_core.errors import AtlasError


class DatasetStatus(StrEnum):
    UPLOADING = "uploading"
    VALIDATING = "validating"
    READY = "ready"
    FAILED = "failed"
    ARCHIVED = "archived"
    DELETED = "deleted"


class DatasetFormat(StrEnum):
    CSV = "csv"
    TSV = "tsv"
    EXCEL = "xlsx"
    JSON = "json"
    PARQUET = "parquet"
    ZIP = "zip"


class UploadJobStatus(StrEnum):
    PENDING = "pending"
    RECEIVING = "receiving"
    VALIDATING = "validating"
    COMPLETED = "completed"
    FAILED = "failed"


SUPPORTED_EXTENSIONS: frozenset[str] = frozenset(
    {".csv", ".tsv", ".xlsx", ".json", ".parquet", ".zip"}
)

EXTENSION_TO_FORMAT: dict[str, DatasetFormat] = {
    ".csv": DatasetFormat.CSV,
    ".tsv": DatasetFormat.TSV,
    ".xlsx": DatasetFormat.EXCEL,
    ".json": DatasetFormat.JSON,
    ".parquet": DatasetFormat.PARQUET,
    ".zip": DatasetFormat.ZIP,
}

MIME_BY_EXTENSION: dict[str, str] = {
    ".csv": "text/csv",
    ".tsv": "text/tab-separated-values",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".json": "application/json",
    ".parquet": "application/vnd.apache.parquet",
    ".zip": "application/zip",
}

# Soft MIME allow-list (browsers often send octet-stream).
ALLOWED_MIMES: frozenset[str] = frozenset(
    {
        *MIME_BY_EXTENSION.values(),
        "application/octet-stream",
        "text/plain",
        "application/x-parquet",
        "application/parquet",
        "application/zip",
        "application/x-zip-compressed",
    }
)

# Zip bomb guardrails
MAX_ZIP_ENTRIES = 500
MAX_ZIP_UNCOMPRESSED_RATIO = 100
MAX_ZIP_UNCOMPRESSED_BYTES = 2 * 1024 * 1024 * 1024  # 2 GiB uncompressed ceiling


class ValidationError(AtlasError):
    """Raised when an uploaded dataset fails validation."""


class ConflictError(AtlasError):
    """Raised on duplicate or conflicting catalog state."""

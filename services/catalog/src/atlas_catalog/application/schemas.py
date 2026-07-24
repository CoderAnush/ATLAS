"""Catalog application schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str | None = None
    description: str = ""
    tags: list[str] = Field(default_factory=list)


class ProjectUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    tags: list[str] | None = None
    is_archived: bool | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    slug: str
    description: str
    owner_user_id: uuid.UUID
    tags: list[str]
    is_archived: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    project_id: uuid.UUID
    name: str
    slug: str
    description: str
    status: str
    format: str
    original_filename: str
    created_by_user_id: uuid.UUID
    current_version: int
    download_count: int
    is_favorite: bool = False
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DatasetVersionResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    version: int
    status: str
    storage_key: str
    storage_filename: str
    original_filename: str
    extension: str
    mime_type: str
    encoding: str | None
    size_bytes: int
    checksum_sha256: str
    row_estimate: int | None
    column_estimate: int | None
    uploaded_by_user_id: uuid.UUID
    error_message: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DatasetMetadataResponse(BaseModel):
    dataset: DatasetResponse
    current: DatasetVersionResponse | None
    tags: list[str]
    storage: dict[str, Any] | None = None
    statistics: dict[str, Any] | None = None


class DatasetListResponse(BaseModel):
    items: list[DatasetResponse]
    total: int
    limit: int
    offset: int


class DownloadResponse(BaseModel):
    url: str
    expires_in_seconds: int
    dataset_id: uuid.UUID
    version: int
    filename: str


class UploadJobResponse(BaseModel):
    id: uuid.UUID
    status: str
    original_filename: str
    received_bytes: int
    parts_received: int
    dataset_id: uuid.UUID | None = None

    model_config = {"from_attributes": True}


class ConnectorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    connector_type: str = Field(pattern="^(sql|s3|stub)$")
    project_id: uuid.UUID | None = None
    config: dict[str, Any] = Field(default_factory=dict)


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    name: str
    connector_type: str
    project_id: uuid.UUID | None
    is_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class CommentResponse(BaseModel):
    id: uuid.UUID
    dataset_id: uuid.UUID
    user_id: uuid.UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}

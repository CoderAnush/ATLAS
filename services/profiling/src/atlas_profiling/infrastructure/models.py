"""SQLAlchemy models for the profiling schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from atlas_core.ids import uuid7
from atlas_db.base import Base
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

JsonType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> uuid.UUID:
    return uuid7()


class ProfilingJobModel(Base):
    __tablename__ = "profiling_jobs"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DatasetProfileModel(Base):
    __tablename__ = "dataset_profiles"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "dataset_id", "dataset_version", name="uq_profile_dataset_ver"
        ),
        {"schema": "profiling"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    dataset_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    dataset_version: Mapped[int] = mapped_column(Integer, nullable=False)
    job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    rows: Mapped[int] = mapped_column(Integer, nullable=False)
    columns: Mapped[int] = mapped_column(Integer, nullable=False)
    memory_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    problem_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_column: Mapped[str | None] = mapped_column(String(255))
    target_confidence: Mapped[float | None] = mapped_column(Float)
    health: Mapped[str] = mapped_column(String(32), nullable=False)
    quality_overall: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    profile_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ColumnProfileModel(Base):
    __tablename__ = "column_profiles"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiling.dataset_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    dtype: Mapped[str] = mapped_column(String(64), nullable=False)
    missing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    unique_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    nearly_constant: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    details: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)


class ColumnStatisticsModel(Base):
    __tablename__ = "column_statistics"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiling.dataset_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    column_name: Mapped[str] = mapped_column(String(255), nullable=False)
    statistics: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)


class QualityReportModel(Base):
    __tablename__ = "quality_reports"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiling.dataset_profiles.id", ondelete="CASCADE"),
        unique=True,
    )
    report: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)


class LeakageReportModel(Base):
    __tablename__ = "leakage_reports"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiling.dataset_profiles.id", ondelete="CASCADE"),
        unique=True,
    )
    report: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)


class ProfilingArtifactModel(Base):
    __tablename__ = "profiling_artifacts"
    __table_args__ = {"schema": "profiling"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiling.dataset_profiles.id", ondelete="CASCADE"),
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(
        String(64), nullable=False
    )  # json|markdown|html|pdf|plotly
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

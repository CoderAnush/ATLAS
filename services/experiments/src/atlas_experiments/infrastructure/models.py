"""SQLAlchemy models for the experiments schema."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from atlas_core.ids import uuid7
from atlas_db.base import Base
from sqlalchemy import (
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

SCHEMA = "experiments"
JsonType = JSON().with_variant(JSONB(), "postgresql")


def _uuid() -> uuid.UUID:
    return uuid7()


class ExperimentModel(Base):
    __tablename__ = "experiments"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="active", index=True)
    group_name: Mapped[str | None] = mapped_column(String(255), index=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    feature_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    algorithm: Mapped[str | None] = mapped_column(String(128), index=True)
    problem_type: Mapped[str | None] = mapped_column(String(64))
    best_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    best_metric_name: Mapped[str | None] = mapped_column(String(128))
    best_metric_value: Mapped[float | None] = mapped_column(Float)
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class ExperimentRunModel(Base):
    __tablename__ = "experiment_runs"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False, default="queued", index=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="training", index=True)
    training_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    hpo_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    hpo_study_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    dataset_version: Mapped[int | None] = mapped_column(Integer)
    feature_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    algorithm: Mapped[str | None] = mapped_column(String(128), index=True)
    problem_type: Mapped[str | None] = mapped_column(String(64))
    random_seed: Mapped[int | None] = mapped_column(Integer)
    git_commit: Mapped[str | None] = mapped_column(String(64))
    atlas_version: Mapped[str | None] = mapped_column(String(32))
    primary_metric: Mapped[str | None] = mapped_column(String(128))
    primary_metric_value: Mapped[float | None] = mapped_column(Float, index=True)
    runtime_seconds: Mapped[float | None] = mapped_column(Float)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mlflow_run_id: Mapped[str | None] = mapped_column(String(128))
    config_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    hyperparameters_json: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    reproducibility_json: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    visualizations_json: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
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


class ExperimentMetricModel(Base):
    __tablename__ = "experiment_metrics"
    __table_args__ = (
        UniqueConstraint("run_id", "metric_name", "step", name="uq_experiments_metric_step"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    split: Mapped[str] = mapped_column(String(32), nullable=False, default="validation")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentArtifactModel(Base):
    __tablename__ = "experiment_artifacts"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    content_type: Mapped[str] = mapped_column(
        String(128), nullable=False, default="application/octet-stream"
    )
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    checksum_sha256: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentParameterModel(Base):
    __tablename__ = "experiment_parameters"
    __table_args__ = (
        UniqueConstraint("run_id", "param_key", name="uq_experiments_param_key"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    param_key: Mapped[str] = mapped_column(String(255), nullable=False)
    param_value: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentEnvironmentModel(Base):
    __tablename__ = "experiment_environment"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    python_version: Mapped[str | None] = mapped_column(String(64))
    os_name: Mapped[str | None] = mapped_column(String(128))
    hardware_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    library_versions_json: Mapped[dict[str, Any]] = mapped_column(
        JsonType, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentTagModel(Base):
    __tablename__ = "experiment_tags"
    __table_args__ = (
        UniqueConstraint("experiment_id", "tag_key", name="uq_experiments_tag_key"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tag_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tag_value: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentNoteModel(Base):
    __tablename__ = "experiment_notes"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    author_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentLineageModel(Base):
    __tablename__ = "experiment_lineage"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        index=True,
    )
    dataset_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dataset_version: Mapped[int | None] = mapped_column(Integer)
    feature_set_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    training_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    hpo_job_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    hpo_study_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    parent_run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    detail_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentComparisonModel(Base):
    __tablename__ = "experiment_comparisons"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, default="comparison")
    run_ids_json: Mapped[list[Any]] = mapped_column(JsonType, nullable=False, default=list)
    result_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class LeaderboardEntryModel(Base):
    __tablename__ = "leaderboard_entries"
    __table_args__ = (
        UniqueConstraint("organization_id", "run_id", name="uq_experiments_leaderboard_run"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    algorithm: Mapped[str | None] = mapped_column(String(128), index=True)
    accuracy: Mapped[float | None] = mapped_column(Float)
    precision: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    f1: Mapped[float | None] = mapped_column(Float)
    loss: Mapped[float | None] = mapped_column(Float)
    runtime_seconds: Mapped[float | None] = mapped_column(Float)
    rank_score: Mapped[float | None] = mapped_column(Float, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentFavoriteModel(Base):
    __tablename__ = "experiment_favorites"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "run_id", name="uq_experiments_favorite"),
        {"schema": SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiment_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ExperimentHistoryModel(Base):
    __tablename__ = "experiment_history"
    __table_args__ = {"schema": SCHEMA}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{SCHEMA}.experiments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    event: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    extra_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

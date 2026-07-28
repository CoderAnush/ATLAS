"""Training engine schema for phase 7.

Revision ID: 0007_training_engine
Revises: 0006_feature_store
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_training_engine"
down_revision: str | None = "0006_feature_store"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS modeling")

    op.create_table(
        "training_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("feature_set_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("eta_seconds", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_jobs_organization_id", "training_jobs", ["organization_id"], schema="modeling")
    op.create_index("ix_training_jobs_feature_set_id", "training_jobs", ["feature_set_id"], schema="modeling")
    op.create_index("ix_training_jobs_dataset_id", "training_jobs", ["dataset_id"], schema="modeling")
    op.create_index("ix_training_jobs_status", "training_jobs", ["status"], schema="modeling")

    op.create_table(
        "trained_models",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("modeling.training_jobs.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("problem_type", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=64), nullable=False),
        sa.Column("target_column", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("model_size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("training_seconds", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("warnings_json", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("report_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_trained_models_organization_id", "trained_models", ["organization_id"], schema="modeling")
    op.create_index("ix_trained_models_job_id", "trained_models", ["job_id"], schema="modeling")
    op.create_index("ix_trained_models_status", "trained_models", ["status"], schema="modeling")

    op.create_table(
        "model_versions",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("trained_model_id", UuidType, sa.ForeignKey("modeling.trained_models.id", ondelete="CASCADE")),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("immutable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("approval_user_id", UuidType, nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_model_versions_organization_id", "model_versions", ["organization_id"], schema="modeling")
    op.create_index("ix_model_versions_trained_model_id", "model_versions", ["trained_model_id"], schema="modeling")

    op.create_table(
        "training_metrics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("trained_model_id", UuidType, sa.ForeignKey("modeling.trained_models.id", ondelete="CASCADE")),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("metric_json", JsonType, nullable=True),
        sa.Column("split", sa.String(length=32), nullable=False, server_default="validation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_metrics_organization_id", "training_metrics", ["organization_id"], schema="modeling")
    op.create_index("ix_training_metrics_model_id", "training_metrics", ["trained_model_id"], schema="modeling")
    op.create_index("ix_training_metrics_name", "training_metrics", ["metric_name"], schema="modeling")

    op.create_table(
        "training_artifacts",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("trained_model_id", UuidType, sa.ForeignKey("modeling.trained_models.id", ondelete="CASCADE")),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_artifacts_organization_id", "training_artifacts", ["organization_id"], schema="modeling")
    op.create_index("ix_training_artifacts_model_id", "training_artifacts", ["trained_model_id"], schema="modeling")

    op.create_table(
        "training_configs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("modeling.training_jobs.id", ondelete="CASCADE")),
        sa.Column("config_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("immutable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_configs_organization_id", "training_configs", ["organization_id"], schema="modeling")
    op.create_index("ix_training_configs_job_id", "training_configs", ["job_id"], schema="modeling")

    op.create_table(
        "training_lineage",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("trained_model_id", UuidType, sa.ForeignKey("modeling.trained_models.id", ondelete="CASCADE")),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column("feature_set_id", UuidType, nullable=False),
        sa.Column("feature_version_id", UuidType, nullable=True),
        sa.Column("preparation_job_id", UuidType, nullable=True),
        sa.Column("git_commit", sa.String(length=128), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=False, server_default=sa.text("42")),
        sa.Column("detail_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_lineage_organization_id", "training_lineage", ["organization_id"], schema="modeling")
    op.create_index("ix_training_lineage_model_id", "training_lineage", ["trained_model_id"], schema="modeling")
    op.create_index("ix_training_lineage_dataset_id", "training_lineage", ["dataset_id"], schema="modeling")

    op.create_table(
        "algorithm_registry",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("family", sa.String(length=64), nullable=False),
        sa.Column("supports_problem_types", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("name", name="uq_algorithm_registry_name"),
        schema="modeling",
    )
    op.create_index("ix_algorithm_registry_name", "algorithm_registry", ["name"], unique=True, schema="modeling")

    op.create_table(
        "training_logs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("modeling.training_jobs.id", ondelete="CASCADE")),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="INFO"),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("extra_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_training_logs_organization_id", "training_logs", ["organization_id"], schema="modeling")
    op.create_index("ix_training_logs_job_id", "training_logs", ["job_id"], schema="modeling")

    op.create_table(
        "model_tags",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("trained_model_id", UuidType, sa.ForeignKey("modeling.trained_models.id", ondelete="CASCADE")),
        sa.Column("tag", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="modeling",
    )
    op.create_index("ix_model_tags_organization_id", "model_tags", ["organization_id"], schema="modeling")
    op.create_index("ix_model_tags_model_id", "model_tags", ["trained_model_id"], schema="modeling")
    op.create_index("ix_model_tags_tag", "model_tags", ["tag"], schema="modeling")


def downgrade() -> None:
    op.drop_table("model_tags", schema="modeling")
    op.drop_table("training_logs", schema="modeling")
    op.drop_table("algorithm_registry", schema="modeling")
    op.drop_table("training_lineage", schema="modeling")
    op.drop_table("training_configs", schema="modeling")
    op.drop_table("training_artifacts", schema="modeling")
    op.drop_table("training_metrics", schema="modeling")
    op.drop_table("model_versions", schema="modeling")
    op.drop_table("trained_models", schema="modeling")
    op.drop_table("training_jobs", schema="modeling")
    op.execute("DROP SCHEMA IF EXISTS modeling CASCADE")

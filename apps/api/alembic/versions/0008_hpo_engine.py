"""Hyperparameter optimization schema for phase 8.

Revision ID: 0008_hpo_engine
Revises: 0007_training_engine
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_hpo_engine"
down_revision: str | None = "0007_training_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS hpo")

    op.create_table(
        "optimization_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "training_job_id", UuidType, sa.ForeignKey("modeling.training_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("feature_set_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("optimizer", sa.String(length=64), nullable=False, server_default="optuna"),
        sa.Column("metric_objective", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("budget_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("config_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("trials_completed", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("remaining_trials", sa.Integer(), nullable=True),
        sa.Column("eta_seconds", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_jobs_organization_id", "optimization_jobs", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_jobs_training_job_id", "optimization_jobs", ["training_job_id"], schema="hpo")
    op.create_index("ix_hpo_jobs_feature_set_id", "optimization_jobs", ["feature_set_id"], schema="hpo")
    op.create_index("ix_hpo_jobs_dataset_id", "optimization_jobs", ["dataset_id"], schema="hpo")
    op.create_index("ix_hpo_jobs_status", "optimization_jobs", ["status"], schema="hpo")

    op.create_table(
        "optimization_studies",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("hpo.optimization_jobs.id", ondelete="CASCADE")),
        sa.Column("study_name", sa.String(length=255), nullable=False),
        sa.Column("optimizer", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="draft"),
        sa.Column("problem_type", sa.String(length=64), nullable=False),
        sa.Column("algorithm", sa.String(length=128), nullable=False),
        sa.Column("metric_objective", sa.String(length=64), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("total_trials", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("completed_trials", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pruned_trials", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("best_trial_number", sa.Integer(), nullable=True),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column("best_params_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("report_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("history_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("approved_by_user_id", UuidType, nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_studies_organization_id", "optimization_studies", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_studies_job_id", "optimization_studies", ["job_id"], schema="hpo")
    op.create_index("ix_hpo_studies_status", "optimization_studies", ["status"], schema="hpo")

    op.create_table(
        "optimization_trials",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("trial_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("objective_value", sa.Float(), nullable=True),
        sa.Column("params_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("metrics_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("user_attrs_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("study_id", "trial_number", name="uq_hpo_trial_number"),
        schema="hpo",
    )
    op.create_index("ix_hpo_trials_organization_id", "optimization_trials", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_trials_study_id", "optimization_trials", ["study_id"], schema="hpo")
    op.create_index("ix_hpo_trials_status", "optimization_trials", ["status"], schema="hpo")

    op.create_table(
        "best_trials",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("trial_id", UuidType, sa.ForeignKey("hpo.optimization_trials.id", ondelete="CASCADE")),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("params_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("metrics_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("report_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("study_id", name="uq_hpo_best_trial_study"),
        sa.UniqueConstraint("trial_id", name="uq_hpo_best_trial_trial"),
        schema="hpo",
    )

    op.create_table(
        "optimization_configs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("hpo.optimization_jobs.id", ondelete="CASCADE")),
        sa.Column("config_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_configs_organization_id", "optimization_configs", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_configs_job_id", "optimization_configs", ["job_id"], schema="hpo")

    op.create_table(
        "optimization_metrics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("metric_json", JsonType, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_metrics_organization_id", "optimization_metrics", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_metrics_study_id", "optimization_metrics", ["study_id"], schema="hpo")
    op.create_index("ix_hpo_metrics_name", "optimization_metrics", ["metric_name"], schema="hpo")

    op.create_table(
        "optimization_artifacts",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_artifacts_organization_id", "optimization_artifacts", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_artifacts_study_id", "optimization_artifacts", ["study_id"], schema="hpo")

    op.create_table(
        "optimization_logs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("job_id", UuidType, sa.ForeignKey("hpo.optimization_jobs.id", ondelete="CASCADE")),
        sa.Column("level", sa.String(length=16), nullable=False, server_default="INFO"),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("extra_json", JsonType, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="hpo",
    )
    op.create_index("ix_hpo_logs_organization_id", "optimization_logs", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_logs_job_id", "optimization_logs", ["job_id"], schema="hpo")
    op.create_index("ix_hpo_logs_event", "optimization_logs", ["event"], schema="hpo")

    op.create_table(
        "search_spaces",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("algorithm", sa.String(length=128), nullable=False),
        sa.Column("search_space_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("study_id", name="uq_hpo_search_space_study"),
        schema="hpo",
    )
    op.create_index("ix_hpo_search_spaces_organization_id", "search_spaces", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_search_spaces_algorithm", "search_spaces", ["algorithm"], schema="hpo")

    op.create_table(
        "optimization_tags",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("study_id", UuidType, sa.ForeignKey("hpo.optimization_studies.id", ondelete="CASCADE")),
        sa.Column("tag_key", sa.String(length=128), nullable=False),
        sa.Column("tag_value", sa.String(length=512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("study_id", "tag_key", name="uq_hpo_tag_key"),
        schema="hpo",
    )
    op.create_index("ix_hpo_tags_organization_id", "optimization_tags", ["organization_id"], schema="hpo")
    op.create_index("ix_hpo_tags_study_id", "optimization_tags", ["study_id"], schema="hpo")


def downgrade() -> None:
    op.drop_table("optimization_tags", schema="hpo")
    op.drop_table("search_spaces", schema="hpo")
    op.drop_table("optimization_logs", schema="hpo")
    op.drop_table("optimization_artifacts", schema="hpo")
    op.drop_table("optimization_metrics", schema="hpo")
    op.drop_table("optimization_configs", schema="hpo")
    op.drop_table("best_trials", schema="hpo")
    op.drop_table("optimization_trials", schema="hpo")
    op.drop_table("optimization_studies", schema="hpo")
    op.drop_table("optimization_jobs", schema="hpo")
    op.execute("DROP SCHEMA IF EXISTS hpo CASCADE")

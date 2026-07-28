"""Experiment tracking schema for phase 9.

Revision ID: 0009_experiments
Revises: 0008_hpo_engine
Create Date: 2026-07-28
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009_experiments"
down_revision: str | None = "0008_hpo_engine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS experiments")

    op.create_table(
        "experiments",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="active"),
        sa.Column("group_name", sa.String(length=255), nullable=True),
        sa.Column("dataset_id", UuidType, nullable=True),
        sa.Column("feature_set_id", UuidType, nullable=True),
        sa.Column("algorithm", sa.String(length=128), nullable=True),
        sa.Column("problem_type", sa.String(length=64), nullable=True),
        sa.Column("best_run_id", UuidType, nullable=True),
        sa.Column("best_metric_name", sa.String(length=128), nullable=True),
        sa.Column("best_metric_value", sa.Float(), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("metadata_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_organization_id", "experiments", ["organization_id"], schema="experiments"
    )
    op.create_index("ix_experiments_name", "experiments", ["name"], schema="experiments")
    op.create_index("ix_experiments_status", "experiments", ["status"], schema="experiments")
    op.create_index(
        "ix_experiments_group_name", "experiments", ["group_name"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_dataset_id", "experiments", ["dataset_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_feature_set_id", "experiments", ["feature_set_id"], schema="experiments"
    )
    op.create_index("ix_experiments_algorithm", "experiments", ["algorithm"], schema="experiments")
    op.create_index(
        "ix_experiments_created_by_user_id",
        "experiments",
        ["created_by_user_id"],
        schema="experiments",
    )

    op.create_table(
        "experiment_runs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False, server_default="queued"),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="training"),
        sa.Column("training_job_id", UuidType, nullable=True),
        sa.Column("hpo_job_id", UuidType, nullable=True),
        sa.Column("hpo_study_id", UuidType, nullable=True),
        sa.Column("dataset_id", UuidType, nullable=True),
        sa.Column("dataset_version", sa.Integer(), nullable=True),
        sa.Column("feature_set_id", UuidType, nullable=True),
        sa.Column("algorithm", sa.String(length=128), nullable=True),
        sa.Column("problem_type", sa.String(length=64), nullable=True),
        sa.Column("random_seed", sa.Integer(), nullable=True),
        sa.Column("git_commit", sa.String(length=64), nullable=True),
        sa.Column("atlas_version", sa.String(length=32), nullable=True),
        sa.Column("primary_metric", sa.String(length=128), nullable=True),
        sa.Column("primary_metric_value", sa.Float(), nullable=True),
        sa.Column("runtime_seconds", sa.Float(), nullable=True),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("favorite", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("mlflow_run_id", sa.String(length=128), nullable=True),
        sa.Column("config_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "hyperparameters_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("metrics_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "reproducibility_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "visualizations_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_organization_id",
        "experiment_runs",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_experiment_id",
        "experiment_runs",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_status", "experiment_runs", ["status"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_runs_source", "experiment_runs", ["source"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_runs_training_job_id",
        "experiment_runs",
        ["training_job_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_hpo_job_id", "experiment_runs", ["hpo_job_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_runs_hpo_study_id",
        "experiment_runs",
        ["hpo_study_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_dataset_id", "experiment_runs", ["dataset_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_runs_feature_set_id",
        "experiment_runs",
        ["feature_set_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_runs_algorithm", "experiment_runs", ["algorithm"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_runs_primary_metric_value",
        "experiment_runs",
        ["primary_metric_value"],
        schema="experiments",
    )

    op.create_table(
        "experiment_metrics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=False),
        sa.Column("step", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("split", sa.String(length=32), nullable=False, server_default="validation"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("run_id", "metric_name", "step", name="uq_experiments_metric_step"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_metrics_organization_id",
        "experiment_metrics",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_metrics_experiment_id",
        "experiment_metrics",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_metrics_run_id", "experiment_metrics", ["run_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_metrics_metric_name",
        "experiment_metrics",
        ["metric_name"],
        schema="experiments",
    )

    op.create_table(
        "experiment_artifacts",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column(
            "content_type",
            sa.String(length=128),
            nullable=False,
            server_default="application/octet-stream",
        ),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_artifacts_organization_id",
        "experiment_artifacts",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_artifacts_experiment_id",
        "experiment_artifacts",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_artifacts_run_id", "experiment_artifacts", ["run_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_artifacts_artifact_type",
        "experiment_artifacts",
        ["artifact_type"],
        schema="experiments",
    )

    op.create_table(
        "experiment_parameters",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("param_key", sa.String(length=255), nullable=False),
        sa.Column("param_value", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("run_id", "param_key", name="uq_experiments_param_key"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_parameters_organization_id",
        "experiment_parameters",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_parameters_experiment_id",
        "experiment_parameters",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_parameters_run_id",
        "experiment_parameters",
        ["run_id"],
        schema="experiments",
    )

    op.create_table(
        "experiment_environment",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("python_version", sa.String(length=64), nullable=True),
        sa.Column("os_name", sa.String(length=128), nullable=True),
        sa.Column("hardware_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "library_versions_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("run_id", name="uq_experiments_environment_run_id"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_environment_organization_id",
        "experiment_environment",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_environment_experiment_id",
        "experiment_environment",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_environment_run_id",
        "experiment_environment",
        ["run_id"],
        schema="experiments",
    )

    op.create_table(
        "experiment_tags",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag_key", sa.String(length=128), nullable=False),
        sa.Column("tag_value", sa.String(length=512), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("experiment_id", "tag_key", name="uq_experiments_tag_key"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_tags_organization_id",
        "experiment_tags",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_tags_experiment_id",
        "experiment_tags",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_tags_tag_key", "experiment_tags", ["tag_key"], schema="experiments"
    )

    op.create_table(
        "experiment_notes",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", UuidType, nullable=True),
        sa.Column("author_user_id", UuidType, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_notes_organization_id",
        "experiment_notes",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_notes_experiment_id",
        "experiment_notes",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_notes_run_id", "experiment_notes", ["run_id"], schema="experiments"
    )

    op.create_table(
        "experiment_lineage",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("dataset_id", UuidType, nullable=True),
        sa.Column("dataset_version", sa.Integer(), nullable=True),
        sa.Column("feature_set_id", UuidType, nullable=True),
        sa.Column("training_job_id", UuidType, nullable=True),
        sa.Column("hpo_job_id", UuidType, nullable=True),
        sa.Column("hpo_study_id", UuidType, nullable=True),
        sa.Column("parent_run_id", UuidType, nullable=True),
        sa.Column("detail_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_lineage_organization_id",
        "experiment_lineage",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_lineage_experiment_id",
        "experiment_lineage",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_lineage_run_id", "experiment_lineage", ["run_id"], schema="experiments"
    )

    op.create_table(
        "experiment_comparisons",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False, server_default="comparison"),
        sa.Column("run_ids_json", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("result_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_comparisons_organization_id",
        "experiment_comparisons",
        ["organization_id"],
        schema="experiments",
    )

    op.create_table(
        "leaderboard_entries",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("algorithm", sa.String(length=128), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1", sa.Float(), nullable=True),
        sa.Column("loss", sa.Float(), nullable=True),
        sa.Column("runtime_seconds", sa.Float(), nullable=True),
        sa.Column("rank_score", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "run_id", name="uq_experiments_leaderboard_run"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_leaderboard_organization_id",
        "leaderboard_entries",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_leaderboard_experiment_id",
        "leaderboard_entries",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_leaderboard_run_id",
        "leaderboard_entries",
        ["run_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_leaderboard_algorithm",
        "leaderboard_entries",
        ["algorithm"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_leaderboard_rank_score",
        "leaderboard_entries",
        ["rank_score"],
        schema="experiments",
    )

    op.create_table(
        "experiment_favorites",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "run_id",
            UuidType,
            sa.ForeignKey("experiments.experiment_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "user_id", "run_id", name="uq_experiments_favorite"),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_favorites_organization_id",
        "experiment_favorites",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_favorites_user_id",
        "experiment_favorites",
        ["user_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_favorites_experiment_id",
        "experiment_favorites",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_favorites_run_id",
        "experiment_favorites",
        ["run_id"],
        schema="experiments",
    )

    op.create_table(
        "experiment_history",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "experiment_id",
            UuidType,
            sa.ForeignKey("experiments.experiments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("run_id", UuidType, nullable=True),
        sa.Column("event", sa.String(length=128), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor_user_id", UuidType, nullable=True),
        sa.Column("extra_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_history_organization_id",
        "experiment_history",
        ["organization_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_history_experiment_id",
        "experiment_history",
        ["experiment_id"],
        schema="experiments",
    )
    op.create_index(
        "ix_experiments_history_run_id", "experiment_history", ["run_id"], schema="experiments"
    )
    op.create_index(
        "ix_experiments_history_event", "experiment_history", ["event"], schema="experiments"
    )


def downgrade() -> None:
    op.drop_table("experiment_history", schema="experiments")
    op.drop_table("experiment_favorites", schema="experiments")
    op.drop_table("leaderboard_entries", schema="experiments")
    op.drop_table("experiment_comparisons", schema="experiments")
    op.drop_table("experiment_lineage", schema="experiments")
    op.drop_table("experiment_notes", schema="experiments")
    op.drop_table("experiment_tags", schema="experiments")
    op.drop_table("experiment_environment", schema="experiments")
    op.drop_table("experiment_parameters", schema="experiments")
    op.drop_table("experiment_artifacts", schema="experiments")
    op.drop_table("experiment_metrics", schema="experiments")
    op.drop_table("experiment_runs", schema="experiments")
    op.drop_table("experiments", schema="experiments")
    op.execute("DROP SCHEMA IF EXISTS experiments CASCADE")

"""Preparation schema: cleaning jobs, plans, recipes, reports, prepared datasets.

Revision ID: 0005_data_preparation
Revises: 0004_dataset_profiling
Create Date: 2026-07-25
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_data_preparation"
down_revision: str | None = "0004_dataset_profiling"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS preparation")

    op.create_table(
        "cleaning_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("strategies", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
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
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_jobs_organization_id",
        "cleaning_jobs",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_jobs_dataset_id", "cleaning_jobs", ["dataset_id"], schema="preparation"
    )
    op.create_index("ix_cleaning_jobs_status", "cleaning_jobs", ["status"], schema="preparation")

    op.create_table(
        "cleaning_plans",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("plan_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_plans_organization_id",
        "cleaning_plans",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index("ix_cleaning_plans_job_id", "cleaning_plans", ["job_id"], schema="preparation")
    op.create_index(
        "ix_cleaning_plans_dataset_id", "cleaning_plans", ["dataset_id"], schema="preparation"
    )

    op.create_table(
        "cleaning_recipes",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column(
            "plan_id", UuidType, sa.ForeignKey("preparation.cleaning_plans.id", ondelete="CASCADE")
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("recipe_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_recipes_organization_id",
        "cleaning_recipes",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_recipes_job_id", "cleaning_recipes", ["job_id"], schema="preparation"
    )
    op.create_index(
        "ix_cleaning_recipes_plan_id", "cleaning_recipes", ["plan_id"], schema="preparation"
    )

    op.create_table(
        "cleaning_steps",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "recipe_id",
            UuidType,
            sa.ForeignKey("preparation.cleaning_recipes.id", ondelete="CASCADE"),
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=True),
        sa.Column("params", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("expected_impact", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved", sa.Boolean(), nullable=True),
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_steps_organization_id",
        "cleaning_steps",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_steps_recipe_id", "cleaning_steps", ["recipe_id"], schema="preparation"
    )

    op.create_table(
        "cleaning_reports",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("report_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("graph_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_reports_organization_id",
        "cleaning_reports",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_cleaning_reports_job_id", "cleaning_reports", ["job_id"], schema="preparation"
    )

    op.create_table(
        "prepared_datasets",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("source_dataset_id", UuidType, nullable=False),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("output_dataset_id", UuidType, nullable=False),
        sa.Column("output_version", sa.Integer(), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("columns", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="preparation",
    )
    op.create_index(
        "ix_prepared_datasets_organization_id",
        "prepared_datasets",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_prepared_datasets_job_id", "prepared_datasets", ["job_id"], schema="preparation"
    )
    op.create_index(
        "ix_prepared_datasets_source_dataset_id",
        "prepared_datasets",
        ["source_dataset_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_prepared_datasets_output_dataset_id",
        "prepared_datasets",
        ["output_dataset_id"],
        schema="preparation",
    )

    op.create_table(
        "quality_improvements",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("before_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("after_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("delta_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("quality_before", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("quality_after", sa.Float(), nullable=False, server_default=sa.text("0")),
        schema="preparation",
    )
    op.create_index(
        "ix_quality_improvements_organization_id",
        "quality_improvements",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_quality_improvements_job_id", "quality_improvements", ["job_id"], schema="preparation"
    )

    op.create_table(
        "transformation_history",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("preparation.cleaning_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("event", sa.String(length=64), nullable=False),
        sa.Column("detail", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="preparation",
    )
    op.create_index(
        "ix_transformation_history_organization_id",
        "transformation_history",
        ["organization_id"],
        schema="preparation",
    )
    op.create_index(
        "ix_transformation_history_job_id",
        "transformation_history",
        ["job_id"],
        schema="preparation",
    )


def downgrade() -> None:
    op.drop_table("transformation_history", schema="preparation")
    op.drop_table("quality_improvements", schema="preparation")
    op.drop_table("prepared_datasets", schema="preparation")
    op.drop_table("cleaning_reports", schema="preparation")
    op.drop_table("cleaning_steps", schema="preparation")
    op.drop_table("cleaning_recipes", schema="preparation")
    op.drop_table("cleaning_plans", schema="preparation")
    op.drop_table("cleaning_jobs", schema="preparation")
    op.execute("DROP SCHEMA IF EXISTS preparation CASCADE")

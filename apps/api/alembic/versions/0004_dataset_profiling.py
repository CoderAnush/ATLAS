"""Profiling schema: jobs, profiles, statistics, quality and leakage reports.

Revision ID: 0004_dataset_profiling
Revises: 0003_dataset_catalog
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_dataset_profiling"
down_revision: str | None = "0003_dataset_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS profiling")

    op.create_table(
        "profiling_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
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
        schema="profiling",
    )
    op.create_index(
        "ix_profiling_jobs_organization_id",
        "profiling_jobs",
        ["organization_id"],
        schema="profiling",
    )
    op.create_index(
        "ix_profiling_jobs_dataset_id", "profiling_jobs", ["dataset_id"], schema="profiling"
    )
    op.create_index("ix_profiling_jobs_status", "profiling_jobs", ["status"], schema="profiling")

    op.create_table(
        "dataset_profiles",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column("job_id", UuidType, nullable=True),
        sa.Column("rows", sa.Integer(), nullable=False),
        sa.Column("columns", sa.Integer(), nullable=False),
        sa.Column("memory_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("problem_type", sa.String(length=64), nullable=False),
        sa.Column("target_column", sa.String(length=255), nullable=True),
        sa.Column("target_confidence", sa.Float(), nullable=True),
        sa.Column("health", sa.String(length=32), nullable=False),
        sa.Column("quality_overall", sa.Float(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("profile_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "organization_id", "dataset_id", "dataset_version", name="uq_profile_dataset_ver"
        ),
        schema="profiling",
    )
    op.create_index(
        "ix_dataset_profiles_organization_id",
        "dataset_profiles",
        ["organization_id"],
        schema="profiling",
    )
    op.create_index(
        "ix_dataset_profiles_dataset_id", "dataset_profiles", ["dataset_id"], schema="profiling"
    )
    op.create_index(
        "ix_dataset_profiles_job_id", "dataset_profiles", ["job_id"], schema="profiling"
    )

    op.create_table(
        "column_profiles",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("profile_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("dtype", sa.String(length=64), nullable=False),
        sa.Column("missing", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_pct", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("unique_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("nearly_constant", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("details", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiling.dataset_profiles.id"], ondelete="CASCADE"
        ),
        schema="profiling",
    )
    op.create_index(
        "ix_column_profiles_organization_id",
        "column_profiles",
        ["organization_id"],
        schema="profiling",
    )
    op.create_index(
        "ix_column_profiles_profile_id", "column_profiles", ["profile_id"], schema="profiling"
    )

    op.create_table(
        "column_statistics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("profile_id", UuidType, nullable=False),
        sa.Column("column_name", sa.String(length=255), nullable=False),
        sa.Column("statistics", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiling.dataset_profiles.id"], ondelete="CASCADE"
        ),
        schema="profiling",
    )
    op.create_index(
        "ix_column_statistics_organization_id",
        "column_statistics",
        ["organization_id"],
        schema="profiling",
    )
    op.create_index(
        "ix_column_statistics_profile_id", "column_statistics", ["profile_id"], schema="profiling"
    )

    op.create_table(
        "quality_reports",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("profile_id", UuidType, nullable=False),
        sa.Column("report", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiling.dataset_profiles.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("profile_id"),
        schema="profiling",
    )
    op.create_index(
        "ix_quality_reports_organization_id",
        "quality_reports",
        ["organization_id"],
        schema="profiling",
    )

    op.create_table(
        "leakage_reports",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("profile_id", UuidType, nullable=False),
        sa.Column("report", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiling.dataset_profiles.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("profile_id"),
        schema="profiling",
    )
    op.create_index(
        "ix_leakage_reports_organization_id",
        "leakage_reports",
        ["organization_id"],
        schema="profiling",
    )

    op.create_table(
        "profiling_artifacts",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("profile_id", UuidType, nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["profiling.dataset_profiles.id"], ondelete="CASCADE"
        ),
        schema="profiling",
    )
    op.create_index(
        "ix_profiling_artifacts_organization_id",
        "profiling_artifacts",
        ["organization_id"],
        schema="profiling",
    )
    op.create_index(
        "ix_profiling_artifacts_profile_id",
        "profiling_artifacts",
        ["profile_id"],
        schema="profiling",
    )


def downgrade() -> None:
    op.drop_table("profiling_artifacts", schema="profiling")
    op.drop_table("leakage_reports", schema="profiling")
    op.drop_table("quality_reports", schema="profiling")
    op.drop_table("column_statistics", schema="profiling")
    op.drop_table("column_profiles", schema="profiling")
    op.drop_table("dataset_profiles", schema="profiling")
    op.drop_table("profiling_jobs", schema="profiling")
    op.execute("DROP SCHEMA IF EXISTS profiling CASCADE")

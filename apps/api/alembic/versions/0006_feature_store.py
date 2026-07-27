"""Feature store schema: jobs, sets, versions, views, registry, lineage, metadata, tags, statistics, transformations.

Revision ID: 0006_feature_store
Revises: 0005_data_preparation
Create Date: 2026-07-27
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_feature_store"
down_revision: str | None = "0005_data_preparation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS feature_store")

    # feature_jobs
    op.create_table(
        "feature_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="queued"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("config", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("history_json", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
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
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_jobs_organization_id",
        "feature_jobs",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_jobs_dataset_id", "feature_jobs", ["dataset_id"], schema="feature_store"
    )
    op.create_index("ix_feature_jobs_status", "feature_jobs", ["status"], schema="feature_store")

    # feature_sets
    op.create_table(
        "feature_sets",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "job_id", UuidType, sa.ForeignKey("feature_store.feature_jobs.id", ondelete="CASCADE")
        ),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="draft"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "selected_features", JsonType, nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column(
            "rejected_features", JsonType, nullable=False, server_default=sa.text("'[]'::json")
        ),
        sa.Column("pipeline_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("report_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("graph_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "recommendations_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")
        ),
        sa.Column("matrix_storage_key", sa.String(length=1024), nullable=True),
        sa.Column("rows", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("columns", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("quality_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("output_dataset_version", sa.Integer(), nullable=True),
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
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_sets_organization_id",
        "feature_sets",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index("ix_feature_sets_job_id", "feature_sets", ["job_id"], schema="feature_store")
    op.create_index(
        "ix_feature_sets_dataset_id", "feature_sets", ["dataset_id"], schema="feature_store"
    )

    # feature_versions
    op.create_table(
        "feature_versions",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "feature_set_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_sets.id", ondelete="CASCADE"),
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("pipeline_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version", sa.Integer(), nullable=False),
        sa.Column("immutable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_versions_organization_id",
        "feature_versions",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_versions_feature_set_id",
        "feature_versions",
        ["feature_set_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_versions_dataset_id",
        "feature_versions",
        ["dataset_id"],
        schema="feature_store",
    )

    # feature_views
    op.create_table(
        "feature_views",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "feature_set_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_sets.id", ondelete="CASCADE"),
        ),
        sa.Column(
            "feature_version_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("feature_names", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("offline_key", sa.String(length=1024), nullable=False),
        sa.Column("online_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_views_organization_id",
        "feature_views",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_views_feature_set_id",
        "feature_views",
        ["feature_set_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_views_feature_version_id",
        "feature_views",
        ["feature_version_id"],
        schema="feature_store",
    )

    # feature_registry
    op.create_table(
        "feature_registry",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "feature_set_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_sets.id", ondelete="CASCADE"),
        ),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("dtype", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("usefulness_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("selected", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("owner_user_id", UuidType, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_registry_organization_id",
        "feature_registry",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_registry_feature_set_id",
        "feature_registry",
        ["feature_set_id"],
        schema="feature_store",
    )

    # feature_lineage
    op.create_table(
        "feature_lineage",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "feature_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_registry.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "feature_set_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_sets.id", ondelete="CASCADE"),
        ),
        sa.Column("parent_type", sa.String(length=64), nullable=False),
        sa.Column("parent_id", sa.String(length=255), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("detail_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_lineage_organization_id",
        "feature_lineage",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_lineage_feature_id",
        "feature_lineage",
        ["feature_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_lineage_feature_set_id",
        "feature_lineage",
        ["feature_set_id"],
        schema="feature_store",
    )

    # feature_metadata
    op.create_table(
        "feature_metadata",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", UuidType, nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_metadata_organization_id",
        "feature_metadata",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_metadata_entity_type",
        "feature_metadata",
        ["entity_type"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_metadata_entity_id",
        "feature_metadata",
        ["entity_id"],
        schema="feature_store",
    )

    # feature_tags
    op.create_table(
        "feature_tags",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "feature_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_registry.id", ondelete="CASCADE"),
        ),
        sa.Column("tag", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_tags_organization_id",
        "feature_tags",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_tags_feature_id", "feature_tags", ["feature_id"], schema="feature_store"
    )
    op.create_index("ix_feature_tags_tag", "feature_tags", ["tag"], schema="feature_store")

    # feature_statistics
    op.create_table(
        "feature_statistics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "feature_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_registry.id", ondelete="CASCADE"),
        ),
        sa.Column("stats_json", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("uniqueness", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("variance", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("missing_pct", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("correlation", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("redundancy", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column("overall_score", sa.Float(), nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_statistics_organization_id",
        "feature_statistics",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_statistics_feature_id",
        "feature_statistics",
        ["feature_id"],
        schema="feature_store",
    )

    # feature_transformations
    op.create_table(
        "feature_transformations",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column(
            "feature_set_id",
            UuidType,
            sa.ForeignKey("feature_store.feature_sets.id", ondelete="CASCADE"),
        ),
        sa.Column("step_order", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("params", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("input_columns", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("output_columns", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("reason", sa.Text(), nullable=False, server_default=""),
        sa.Column("approved", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_transformations_organization_id",
        "feature_transformations",
        ["organization_id"],
        schema="feature_store",
    )
    op.create_index(
        "ix_feature_transformations_feature_set_id",
        "feature_transformations",
        ["feature_set_id"],
        schema="feature_store",
    )


def downgrade() -> None:
    op.drop_table("feature_transformations", schema="feature_store")
    op.drop_table("feature_statistics", schema="feature_store")
    op.drop_table("feature_tags", schema="feature_store")
    op.drop_table("feature_metadata", schema="feature_store")
    op.drop_table("feature_lineage", schema="feature_store")
    op.drop_table("feature_registry", schema="feature_store")
    op.drop_table("feature_views", schema="feature_store")
    op.drop_table("feature_versions", schema="feature_store")
    op.drop_table("feature_sets", schema="feature_store")
    op.drop_table("feature_jobs", schema="feature_store")
    op.execute("DROP SCHEMA IF EXISTS feature_store CASCADE")

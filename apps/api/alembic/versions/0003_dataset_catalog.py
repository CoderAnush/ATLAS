"""Catalog schema: projects, datasets, versions, tags, permissions, uploads.

Revision ID: 0003_dataset_catalog
Revises: 0002_identity_auth
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_dataset_catalog"
down_revision: str | None = "0002_identity_auth"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS catalog")

    op.create_table(
        "projects",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("owner_user_id", UuidType, nullable=False),
        sa.Column("tags", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("organization_id", "slug", name="uq_catalog_project_org_slug"),
        schema="catalog",
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"], schema="catalog")
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"], schema="catalog")

    op.create_table(
        "datasets",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("project_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=140), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("format", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("download_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_favorite_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["catalog.projects.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "project_id", "slug", name="uq_catalog_dataset_project_slug"),
        schema="catalog",
    )
    op.create_index("ix_datasets_organization_id", "datasets", ["organization_id"], schema="catalog")
    op.create_index("ix_datasets_project_id", "datasets", ["project_id"], schema="catalog")
    op.create_index("ix_datasets_status", "datasets", ["status"], schema="catalog")
    op.create_index("ix_catalog_datasets_search", "datasets", ["organization_id", "name"], schema="catalog")

    op.create_table(
        "dataset_versions",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=512), nullable=False),
        sa.Column("storage_filename", sa.String(length=64), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("extension", sa.String(length=16), nullable=False),
        sa.Column("mime_type", sa.String(length=128), nullable=False),
        sa.Column("encoding", sa.String(length=64), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("row_estimate", sa.Integer(), nullable=True),
        sa.Column("column_estimate", sa.Integer(), nullable=True),
        sa.Column("uploaded_by_user_id", UuidType, nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["catalog.datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "version", name="uq_catalog_dataset_version"),
        schema="catalog",
    )
    op.create_index("ix_dataset_versions_organization_id", "dataset_versions", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_versions_dataset_id", "dataset_versions", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_versions_checksum_sha256", "dataset_versions", ["checksum_sha256"], schema="catalog")

    op.create_table(
        "dataset_tags",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("tag", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["catalog.datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "tag", name="uq_catalog_dataset_tag"),
        schema="catalog",
    )
    op.create_index("ix_dataset_tags_organization_id", "dataset_tags", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_tags_dataset_id", "dataset_tags", ["dataset_id"], schema="catalog")

    op.create_table(
        "dataset_permissions",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="viewer"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["catalog.datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "user_id", name="uq_catalog_dataset_perm"),
        schema="catalog",
    )
    op.create_index("ix_dataset_permissions_organization_id", "dataset_permissions", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_permissions_dataset_id", "dataset_permissions", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_permissions_user_id", "dataset_permissions", ["user_id"], schema="catalog")

    op.create_table(
        "dataset_upload_jobs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("project_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=True),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("expected_size", sa.BigInteger(), nullable=True),
        sa.Column("received_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("temp_storage_key", sa.String(length=512), nullable=True),
        sa.Column("parts_received", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="catalog",
    )
    op.create_index("ix_dataset_upload_jobs_organization_id", "dataset_upload_jobs", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_upload_jobs_project_id", "dataset_upload_jobs", ["project_id"], schema="catalog")
    op.create_index("ix_dataset_upload_jobs_dataset_id", "dataset_upload_jobs", ["dataset_id"], schema="catalog")

    op.create_table(
        "dataset_connectors",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("project_id", UuidType, nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("connector_type", sa.String(length=64), nullable=False),
        sa.Column("config", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by_user_id", UuidType, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="catalog",
    )
    op.create_index("ix_dataset_connectors_organization_id", "dataset_connectors", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_connectors_project_id", "dataset_connectors", ["project_id"], schema="catalog")

    op.create_table(
        "dataset_lineage",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("parent_dataset_id", UuidType, nullable=True),
        sa.Column("parent_version_id", UuidType, nullable=True),
        sa.Column("relation", sa.String(length=64), nullable=False, server_default="derived_from"),
        sa.Column("metadata", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="catalog",
    )
    op.create_index("ix_dataset_lineage_organization_id", "dataset_lineage", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_lineage_dataset_id", "dataset_lineage", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_lineage_parent_dataset_id", "dataset_lineage", ["parent_dataset_id"], schema="catalog")

    op.create_table(
        "dataset_storage",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_version_id", UuidType, nullable=False),
        sa.Column("bucket", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.String(length=512), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=True),
        sa.Column("storage_class", sa.String(length=64), nullable=False, server_default="STANDARD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["catalog.dataset_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_version_id"),
        schema="catalog",
    )
    op.create_index("ix_dataset_storage_organization_id", "dataset_storage", ["organization_id"], schema="catalog")

    op.create_table(
        "dataset_statistics",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_version_id", UuidType, nullable=False),
        sa.Column("row_estimate", sa.Integer(), nullable=True),
        sa.Column("column_estimate", sa.Integer(), nullable=True),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("extra", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_version_id"], ["catalog.dataset_versions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_version_id"),
        schema="catalog",
    )
    op.create_index("ix_dataset_statistics_organization_id", "dataset_statistics", ["organization_id"], schema="catalog")

    op.create_table(
        "dataset_download_logs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("dataset_version_id", UuidType, nullable=True),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="catalog",
    )
    op.create_index("ix_dataset_download_logs_organization_id", "dataset_download_logs", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_download_logs_dataset_id", "dataset_download_logs", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_download_logs_user_id", "dataset_download_logs", ["user_id"], schema="catalog")
    op.create_index("ix_dataset_download_logs_created_at", "dataset_download_logs", ["created_at"], schema="catalog")

    op.create_table(
        "dataset_favorites",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["catalog.datasets.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("dataset_id", "user_id", name="uq_catalog_dataset_favorite"),
        schema="catalog",
    )
    op.create_index("ix_dataset_favorites_organization_id", "dataset_favorites", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_favorites_dataset_id", "dataset_favorites", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_favorites_user_id", "dataset_favorites", ["user_id"], schema="catalog")

    op.create_table(
        "dataset_comments",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("dataset_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id"], ["catalog.datasets.id"], ondelete="CASCADE"),
        schema="catalog",
    )
    op.create_index("ix_dataset_comments_organization_id", "dataset_comments", ["organization_id"], schema="catalog")
    op.create_index("ix_dataset_comments_dataset_id", "dataset_comments", ["dataset_id"], schema="catalog")
    op.create_index("ix_dataset_comments_user_id", "dataset_comments", ["user_id"], schema="catalog")


def downgrade() -> None:
    op.drop_table("dataset_comments", schema="catalog")
    op.drop_table("dataset_favorites", schema="catalog")
    op.drop_table("dataset_download_logs", schema="catalog")
    op.drop_table("dataset_statistics", schema="catalog")
    op.drop_table("dataset_storage", schema="catalog")
    op.drop_table("dataset_lineage", schema="catalog")
    op.drop_table("dataset_connectors", schema="catalog")
    op.drop_table("dataset_upload_jobs", schema="catalog")
    op.drop_table("dataset_permissions", schema="catalog")
    op.drop_table("dataset_tags", schema="catalog")
    op.drop_table("dataset_versions", schema="catalog")
    op.drop_table("datasets", schema="catalog")
    op.drop_table("projects", schema="catalog")
    op.execute("DROP SCHEMA IF EXISTS catalog CASCADE")

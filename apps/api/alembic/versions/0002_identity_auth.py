"""Identity schema: users, orgs, RBAC, sessions, API keys, audit.

Revision ID: 0002_identity_auth
Revises: 0001_platform_foundation
Create Date: 2026-07-24
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_identity_auth"
down_revision: str | None = "0001_platform_foundation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql")
UuidType = sa.Uuid(as_uuid=True)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS identity")

    op.create_table(
        "organizations",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("settings", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_by_user_id", UuidType, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="identity",
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True, schema="identity")

    op.create_table(
        "users",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("email_verification_token", sa.String(length=128), nullable=True),
        sa.Column("password_reset_token", sa.String(length=128), nullable=True),
        sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_organization_id", UuidType, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["active_organization_id"], ["identity.organizations.id"], ondelete="SET NULL"),
        schema="identity",
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True, schema="identity")

    op.create_table(
        "memberships",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("invited_email", sa.String(length=320), nullable=True),
        sa.Column("invite_token", sa.String(length=128), nullable=True),
        sa.Column("invite_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["identity.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),
        schema="identity",
    )
    op.create_index("ix_memberships_organization_id", "memberships", ["organization_id"], schema="identity")
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"], schema="identity")

    op.create_table(
        "projects",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["identity.organizations.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("organization_id", "slug", name="uq_project_org_slug"),
        schema="identity",
    )
    op.create_index("ix_projects_organization_id", "projects", ["organization_id"], schema="identity")

    op.create_table(
        "project_memberships",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("project_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["identity.projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("project_id", "user_id", name="uq_project_member"),
        schema="identity",
    )

    op.create_table(
        "sessions",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("organization_id", UuidType, nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["identity.users.id"], ondelete="CASCADE"),
        schema="identity",
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], schema="identity")

    op.create_table(
        "refresh_tokens",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("session_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("token_hash", sa.String(length=128), nullable=False),
        sa.Column("family_id", UuidType, nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", UuidType, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["identity.sessions.id"], ondelete="CASCADE"),
        schema="identity",
    )
    op.create_index("ix_refresh_token_hash", "refresh_tokens", ["token_hash"], unique=True, schema="identity")
    op.create_index("ix_refresh_tokens_family_id", "refresh_tokens", ["family_id"], schema="identity")
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"], schema="identity")

    op.create_table(
        "api_keys",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=False),
        sa.Column("user_id", UuidType, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False),
        sa.Column("scopes", JsonType, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["identity.organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["identity.users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("key_hash"),
        schema="identity",
    )
    op.create_index("ix_api_keys_organization_id", "api_keys", ["organization_id"], schema="identity")
    op.create_index("ix_api_keys_prefix", "api_keys", ["prefix"], schema="identity")

    op.create_table(
        "audit_logs",
        sa.Column("id", UuidType, primary_key=True, nullable=False),
        sa.Column("organization_id", UuidType, nullable=True),
        sa.Column("user_id", UuidType, nullable=True),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=64), nullable=True),
        sa.Column("resource_id", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("metadata", JsonType, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        schema="identity",
    )
    op.create_index("ix_audit_logs_organization_id", "audit_logs", ["organization_id"], schema="identity")
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"], schema="identity")
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"], schema="identity")
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"], schema="identity")


def downgrade() -> None:
    op.drop_table("audit_logs", schema="identity")
    op.drop_table("api_keys", schema="identity")
    op.drop_table("refresh_tokens", schema="identity")
    op.drop_table("sessions", schema="identity")
    op.drop_table("project_memberships", schema="identity")
    op.drop_table("projects", schema="identity")
    op.drop_table("memberships", schema="identity")
    op.drop_table("users", schema="identity")
    op.drop_table("organizations", schema="identity")
    op.execute("DROP SCHEMA IF EXISTS identity CASCADE")

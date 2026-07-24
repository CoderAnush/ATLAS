"""Tenant-aware repository helpers — all queries filter by organization_id."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from atlas_identity.infrastructure.models import (
    ApiKeyModel,
    AuditLogModel,
    MembershipModel,
    OrganizationModel,
    ProjectMembershipModel,
    ProjectModel,
    RefreshTokenModel,
    SessionModel,
    UserModel,
)


def utcnow() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)


def ensure_aware(value: datetime) -> datetime:
    """Normalize SQLite naive datetimes to UTC-aware."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class IdentityRepository:
    """Persistence access with mandatory tenant filters on org-scoped entities."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # --- users ---
    def get_user_by_email(self, email: str) -> UserModel | None:
        return self.session.scalar(select(UserModel).where(UserModel.email == email.lower()))

    def get_user(self, user_id: uuid.UUID) -> UserModel | None:
        return self.session.get(UserModel, user_id)

    def add_user(self, user: UserModel) -> UserModel:
        self.session.add(user)
        self.session.flush()
        return user

    # --- organizations ---
    def get_organization(self, org_id: uuid.UUID) -> OrganizationModel | None:
        return self.session.get(OrganizationModel, org_id)

    def get_organization_by_slug(self, slug: str) -> OrganizationModel | None:
        return self.session.scalar(select(OrganizationModel).where(OrganizationModel.slug == slug))

    def add_organization(self, org: OrganizationModel) -> OrganizationModel:
        self.session.add(org)
        self.session.flush()
        return org

    def list_organizations_for_user(self, user_id: uuid.UUID) -> list[OrganizationModel]:
        stmt = (
            select(OrganizationModel)
            .join(MembershipModel, MembershipModel.organization_id == OrganizationModel.id)
            .where(MembershipModel.user_id == user_id)
            .order_by(OrganizationModel.name)
        )
        return list(self.session.scalars(stmt))

    # --- memberships ---
    def get_membership(self, org_id: uuid.UUID, user_id: uuid.UUID) -> MembershipModel | None:
        return self.session.scalar(
            select(MembershipModel).where(
                MembershipModel.organization_id == org_id,
                MembershipModel.user_id == user_id,
            )
        )

    def list_memberships(self, org_id: uuid.UUID) -> list[MembershipModel]:
        return list(
            self.session.scalars(
                select(MembershipModel).where(MembershipModel.organization_id == org_id)
            )
        )

    def add_membership(self, membership: MembershipModel) -> MembershipModel:
        self.session.add(membership)
        self.session.flush()
        return membership

    # --- projects (tenant scoped) ---
    def tenant_projects(self, org_id: uuid.UUID) -> Select[tuple[ProjectModel]]:
        return select(ProjectModel).where(ProjectModel.organization_id == org_id)

    def get_project(self, org_id: uuid.UUID, project_id: uuid.UUID) -> ProjectModel | None:
        return self.session.scalar(
            select(ProjectModel).where(
                ProjectModel.organization_id == org_id,
                ProjectModel.id == project_id,
            )
        )

    def add_project(self, project: ProjectModel) -> ProjectModel:
        self.session.add(project)
        self.session.flush()
        return project

    def get_project_membership(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> ProjectMembershipModel | None:
        return self.session.scalar(
            select(ProjectMembershipModel).where(
                ProjectMembershipModel.project_id == project_id,
                ProjectMembershipModel.user_id == user_id,
            )
        )

    def add_project_membership(self, row: ProjectMembershipModel) -> ProjectMembershipModel:
        self.session.add(row)
        self.session.flush()
        return row

    # --- sessions / tokens ---
    def add_session(self, session_row: SessionModel) -> SessionModel:
        self.session.add(session_row)
        self.session.flush()
        return session_row

    def get_session(self, session_id: uuid.UUID) -> SessionModel | None:
        return self.session.get(SessionModel, session_id)

    def add_refresh_token(self, token: RefreshTokenModel) -> RefreshTokenModel:
        self.session.add(token)
        self.session.flush()
        return token

    def get_refresh_by_hash(self, token_hash: str) -> RefreshTokenModel | None:
        return self.session.scalar(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )

    def revoke_refresh_family(self, family_id: uuid.UUID) -> None:
        tokens = self.session.scalars(
            select(RefreshTokenModel).where(
                RefreshTokenModel.family_id == family_id,
                RefreshTokenModel.revoked_at.is_(None),
            )
        )
        now = utcnow()
        for token in tokens:
            token.revoked_at = now

    # --- api keys (tenant scoped) ---
    def list_api_keys(self, org_id: uuid.UUID) -> list[ApiKeyModel]:
        return list(
            self.session.scalars(
                select(ApiKeyModel).where(
                    ApiKeyModel.organization_id == org_id,
                    ApiKeyModel.revoked_at.is_(None),
                )
            )
        )

    def get_api_key(self, org_id: uuid.UUID, key_id: uuid.UUID) -> ApiKeyModel | None:
        return self.session.scalar(
            select(ApiKeyModel).where(
                ApiKeyModel.organization_id == org_id,
                ApiKeyModel.id == key_id,
            )
        )

    def get_api_key_by_hash(self, key_hash: str) -> ApiKeyModel | None:
        return self.session.scalar(select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash))

    def add_api_key(self, key: ApiKeyModel) -> ApiKeyModel:
        self.session.add(key)
        self.session.flush()
        return key

    # --- audit ---
    def add_audit(self, row: AuditLogModel) -> AuditLogModel:
        self.session.add(row)
        self.session.flush()
        return row

    def list_audit(self, org_id: uuid.UUID, *, limit: int = 100) -> Iterable[AuditLogModel]:
        stmt = (
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == org_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return self.session.scalars(stmt)

"""Identity application services — auth, orgs, API keys, audit."""

from __future__ import annotations

import re
import secrets
import uuid
from datetime import timedelta
from typing import Any

from atlas_core.errors import AtlasError, NotFoundError
from atlas_telemetry.request_context import get_request_id

from atlas_identity.domain.rbac import OrgRole, Permission, has_permission, permissions_for
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
from atlas_identity.infrastructure.password import (
    hash_password,
    validate_password_policy,
    verify_password,
)
from atlas_identity.infrastructure.repository import IdentityRepository, ensure_aware, utcnow
from atlas_identity.infrastructure.security import (
    TokenSettings,
    create_access_token,
    hash_token,
    new_api_key_material,
    new_refresh_token,
)


class AuthError(AtlasError):
    """Authentication failure (maps to HTTP 401)."""


class ForbiddenError(AtlasError):
    """Authorization failure (maps to HTTP 403)."""


class ConflictError(AtlasError):
    """Resource conflict (maps to HTTP 409)."""


class RateLimitError(AtlasError):
    """Too many attempts (maps to HTTP 429)."""


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:100] or f"org-{secrets.token_hex(3)}"


class IdentityService:
    """Application service orchestrating identity use cases."""

    def __init__(
        self,
        repo: IdentityRepository,
        token_settings: TokenSettings,
        *,
        mailer: Any | None = None,
    ) -> None:
        self.repo = repo
        self.tokens = token_settings
        self.mailer = mailer  # stub / future provider

    def _audit(
        self,
        action: str,
        *,
        user_id: uuid.UUID | None = None,
        org_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        ip: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.repo.add_audit(
            AuditLogModel(
                organization_id=org_id,
                user_id=user_id,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=ip,
                request_id=get_request_id(),
                metadata_json=metadata or {},
            )
        )

    def require_org_permission(
        self, user_id: uuid.UUID, org_id: uuid.UUID, permission: Permission
    ) -> MembershipModel:
        membership = self.repo.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        role = OrgRole(membership.role)
        if not has_permission(role, permission):
            raise ForbiddenError(f"missing permission {permission}")
        return membership

    def register(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        organization_name: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[UserModel, OrganizationModel, dict[str, Any]]:
        if self.repo.get_user_by_email(email):
            raise ConflictError("email already registered")
        validate_password_policy(password)
        user = UserModel(
            email=email.lower().strip(),
            password_hash=hash_password(password),
            full_name=full_name.strip(),
            is_email_verified=False,
            email_verification_token=secrets.token_urlsafe(32),
        )
        self.repo.add_user(user)
        org = self._create_org(user, organization_name)
        user.active_organization_id = org.id
        self.repo.session.flush()
        self._audit("user.registered", user_id=user.id, org_id=org.id, ip=ip)
        self._audit("organization.created", user_id=user.id, org_id=org.id, ip=ip)
        # Email verification architecture (mailer stubbed)
        if self.mailer is not None:
            self.mailer.send_verification(user.email, user.email_verification_token)
        tokens = self._issue_session(user, org, OrgRole.OWNER, ip=ip, user_agent=user_agent)
        return user, org, tokens

    def _create_org(self, user: UserModel, name: str) -> OrganizationModel:
        base = _slugify(name)
        slug = base
        i = 1
        while self.repo.get_organization_by_slug(slug):
            slug = f"{base}-{i}"
            i += 1
        org = OrganizationModel(name=name.strip(), slug=slug, created_by_user_id=user.id, settings={})
        self.repo.add_organization(org)
        self.repo.add_membership(
            MembershipModel(
                organization_id=org.id,
                user_id=user.id,
                role=OrgRole.OWNER.value,
                invite_accepted_at=utcnow(),
            )
        )
        return org

    def login(
        self,
        *,
        email: str,
        password: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        user = self.repo.get_user_by_email(email)
        if user is None or not user.is_active or not verify_password(user.password_hash, password):
            self._audit("auth.login_failed", ip=ip, metadata={"email": email.lower()})
            raise AuthError("invalid credentials")
        org = None
        role = None
        if user.active_organization_id:
            org = self.repo.get_organization(user.active_organization_id)
            membership = self.repo.get_membership(user.active_organization_id, user.id)
            if membership:
                role = OrgRole(membership.role)
        if org is None:
            orgs = self.repo.list_organizations_for_user(user.id)
            if orgs:
                org = orgs[0]
                membership = self.repo.get_membership(org.id, user.id)
                role = OrgRole(membership.role) if membership else OrgRole.VIEWER
                user.active_organization_id = org.id
        self._audit("auth.login", user_id=user.id, org_id=org.id if org else None, ip=ip)
        return self._issue_session(user, org, role, ip=ip, user_agent=user_agent)

    def _issue_session(
        self,
        user: UserModel,
        org: OrganizationModel | None,
        role: OrgRole | None,
        *,
        ip: str | None,
        user_agent: str | None,
    ) -> dict[str, Any]:
        session = SessionModel(
            user_id=user.id,
            organization_id=org.id if org else None,
            user_agent=user_agent,
            ip_address=ip,
            expires_at=utcnow() + timedelta(days=self.tokens.refresh_token_days),
        )
        self.repo.add_session(session)
        raw_refresh = new_refresh_token()
        family_id = uuid.uuid4()
        self.repo.add_refresh_token(
            RefreshTokenModel(
                session_id=session.id,
                user_id=user.id,
                token_hash=hash_token(raw_refresh),
                family_id=family_id,
                expires_at=session.expires_at,
            )
        )
        access, exp = create_access_token(
            settings=self.tokens,
            user_id=user.id,
            session_id=session.id,
            org_id=org.id if org else None,
            role=role.value if role else None,
        )
        return {
            "access_token": access,
            "refresh_token": raw_refresh,
            "token_type": "bearer",
            "expires_in": int((exp - utcnow()).total_seconds()),
            "organization_id": org.id if org else None,
        }

    def refresh(self, refresh_token: str, *, ip: str | None = None) -> dict[str, Any]:
        row = self.repo.get_refresh_by_hash(hash_token(refresh_token))
        if row is None or row.revoked_at is not None or ensure_aware(row.expires_at) < utcnow():
            raise AuthError("invalid refresh token")
        session = self.repo.get_session(row.session_id)
        if session is None or session.revoked_at is not None:
            raise AuthError("session revoked")
        # Rotation: revoke current, issue new in same family
        row.revoked_at = utcnow()
        new_raw = new_refresh_token()
        new_row = RefreshTokenModel(
            session_id=session.id,
            user_id=row.user_id,
            token_hash=hash_token(new_raw),
            family_id=row.family_id,
            expires_at=row.expires_at,
        )
        self.repo.add_refresh_token(new_row)
        row.replaced_by_id = new_row.id
        user = self.repo.get_user(row.user_id)
        if user is None or not user.is_active:
            raise AuthError("user inactive")
        org = self.repo.get_organization(session.organization_id) if session.organization_id else None
        role = None
        if org:
            membership = self.repo.get_membership(org.id, user.id)
            role = OrgRole(membership.role) if membership else None
        access, exp = create_access_token(
            settings=self.tokens,
            user_id=user.id,
            session_id=session.id,
            org_id=org.id if org else None,
            role=role.value if role else None,
        )
        self._audit("auth.refresh", user_id=user.id, org_id=org.id if org else None, ip=ip)
        return {
            "access_token": access,
            "refresh_token": new_raw,
            "token_type": "bearer",
            "expires_in": int((exp - utcnow()).total_seconds()),
            "organization_id": org.id if org else None,
        }

    def logout(self, session_id: uuid.UUID, user_id: uuid.UUID, *, ip: str | None = None) -> None:
        session = self.repo.get_session(session_id)
        if session is None or session.user_id != user_id:
            raise AuthError("invalid session")
        session.revoked_at = utcnow()
        for token in session.refresh_tokens:
            if token.revoked_at is None:
                token.revoked_at = utcnow()
        self._audit(
            "auth.logout",
            user_id=user_id,
            org_id=session.organization_id,
            ip=ip,
        )

    def change_password(
        self, user_id: uuid.UUID, current_password: str, new_password: str, *, ip: str | None = None
    ) -> None:
        user = self.repo.get_user(user_id)
        if user is None or not verify_password(user.password_hash, current_password):
            raise AuthError("invalid credentials")
        validate_password_policy(new_password)
        user.password_hash = hash_password(new_password)
        self._audit("user.password_changed", user_id=user_id, org_id=user.active_organization_id, ip=ip)

    def forgot_password(self, email: str) -> dict[str, str]:
        """Issue a reset token (mailer stubbed — token returned only in non-prod via service)."""
        user = self.repo.get_user_by_email(email)
        detail = "If the account exists, a reset email will be sent."
        if user is None:
            return {"detail": detail, "token": ""}
        user.password_reset_token = secrets.token_urlsafe(32)
        user.password_reset_expires_at = utcnow() + timedelta(hours=1)
        self._audit("user.password_reset_requested", user_id=user.id)
        if self.mailer is not None:
            self.mailer.send_password_reset(user.email, user.password_reset_token)
        return {"detail": detail, "token": user.password_reset_token}

    def reset_password(self, token: str, new_password: str) -> None:
        from sqlalchemy import select

        user = self.repo.session.scalar(
            select(UserModel).where(UserModel.password_reset_token == token)
        )
        if (
            user is None
            or user.password_reset_expires_at is None
            or ensure_aware(user.password_reset_expires_at) < utcnow()
        ):
            raise AuthError("invalid or expired reset token")
        validate_password_policy(new_password)
        user.password_hash = hash_password(new_password)
        user.password_reset_token = None
        user.password_reset_expires_at = None
        self._audit("user.password_reset_completed", user_id=user.id)

    def create_organization(self, user_id: uuid.UUID, name: str, slug: str | None = None) -> OrganizationModel:
        user = self.repo.get_user(user_id)
        if user is None:
            raise NotFoundError("user not found")
        desired = _slugify(slug or name)
        if self.repo.get_organization_by_slug(desired):
            raise ConflictError("organization slug already exists")
        org = OrganizationModel(
            name=name.strip(),
            slug=desired,
            created_by_user_id=user_id,
            settings={},
        )
        self.repo.add_organization(org)
        self.repo.add_membership(
            MembershipModel(
                organization_id=org.id,
                user_id=user_id,
                role=OrgRole.OWNER.value,
                invite_accepted_at=utcnow(),
            )
        )
        if user.active_organization_id is None:
            user.active_organization_id = org.id
        self._audit("organization.created", user_id=user_id, org_id=org.id)
        return org

    def invite_member(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, email: str, role: str
    ) -> MembershipModel:
        self.require_org_permission(actor_id, org_id, Permission.ORG_MANAGE_MEMBERS)
        try:
            OrgRole(role)
        except ValueError as exc:
            raise AtlasError(f"invalid role {role}") from exc
        if role == OrgRole.OWNER.value:
            raise ForbiddenError("cannot invite as owner")
        user = self.repo.get_user_by_email(email)
        invite_token = secrets.token_urlsafe(24)
        if user is None:
            # Pending invite row without user_id is awkward with FK — create placeholder inactive user
            user = UserModel(
                email=email.lower(),
                password_hash=hash_password(f"Tmp!{secrets.token_urlsafe(12)}aA1"),
                full_name=email.split("@")[0],
                is_active=False,
            )
            self.repo.add_user(user)
        existing = self.repo.get_membership(org_id, user.id)
        if existing:
            raise ConflictError("user already a member")
        membership = MembershipModel(
            organization_id=org_id,
            user_id=user.id,
            role=role,
            invited_email=email.lower(),
            invite_token=invite_token,
        )
        self.repo.add_membership(membership)
        self._audit(
            "organization.member_invited",
            user_id=actor_id,
            org_id=org_id,
            metadata={"invitee": email.lower(), "role": role},
        )
        if self.mailer is not None:
            self.mailer.send_invite(email, invite_token)
        return membership

    def switch_organization(self, user_id: uuid.UUID, org_id: uuid.UUID) -> UserModel:
        membership = self.repo.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        user = self.repo.get_user(user_id)
        if user is None:
            raise NotFoundError("user not found")
        user.active_organization_id = org_id
        self._audit("organization.switched", user_id=user_id, org_id=org_id)
        return user

    def create_project(
        self, user_id: uuid.UUID, org_id: uuid.UUID, name: str, slug: str | None, description: str
    ) -> ProjectModel:
        self.require_org_permission(user_id, org_id, Permission.PROJECT_WRITE)
        project_slug = _slugify(slug or name)
        project = ProjectModel(
            organization_id=org_id,
            name=name.strip(),
            slug=project_slug,
            description=description,
        )
        self.repo.add_project(project)
        self.repo.add_project_membership(
            ProjectMembershipModel(project_id=project.id, user_id=user_id, role=OrgRole.OWNER.value)
        )
        self._audit(
            "project.created",
            user_id=user_id,
            org_id=org_id,
            resource_type="project",
            resource_id=str(project.id),
        )
        return project

    def add_project_member(
        self, actor_id: uuid.UUID, org_id: uuid.UUID, project_id: uuid.UUID, user_id: uuid.UUID, role: str
    ) -> ProjectMembershipModel:
        self.require_org_permission(actor_id, org_id, Permission.PROJECT_MANAGE_MEMBERS)
        project = self.repo.get_project(org_id, project_id)
        if project is None:
            raise NotFoundError("project not found")
        if self.repo.get_membership(org_id, user_id) is None:
            raise ForbiddenError("user must belong to the organization")
        row = ProjectMembershipModel(project_id=project_id, user_id=user_id, role=role)
        self.repo.add_project_membership(row)
        self._audit(
            "project.member_added",
            user_id=actor_id,
            org_id=org_id,
            resource_type="project",
            resource_id=str(project_id),
            metadata={"member_id": str(user_id), "role": role},
        )
        return row

    def create_api_key(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        name: str,
        scopes: list[str],
        expires_in_days: int | None,
    ) -> tuple[ApiKeyModel, str]:
        self.require_org_permission(user_id, org_id, Permission.APIKEY_MANAGE)
        prefix, raw, key_hash = new_api_key_material()
        expires_at = None
        if expires_in_days:
            expires_at = utcnow() + timedelta(days=expires_in_days)
        key = ApiKeyModel(
            organization_id=org_id,
            user_id=user_id,
            name=name,
            prefix=prefix,
            key_hash=key_hash,
            scopes=scopes,
            expires_at=expires_at,
        )
        self.repo.add_api_key(key)
        self._audit(
            "apikey.created",
            user_id=user_id,
            org_id=org_id,
            resource_type="api_key",
            resource_id=str(key.id),
        )
        return key, raw

    def revoke_api_key(self, user_id: uuid.UUID, org_id: uuid.UUID, key_id: uuid.UUID) -> None:
        self.require_org_permission(user_id, org_id, Permission.APIKEY_MANAGE)
        key = self.repo.get_api_key(org_id, key_id)
        if key is None:
            raise NotFoundError("api key not found")
        key.revoked_at = utcnow()
        self._audit(
            "apikey.revoked",
            user_id=user_id,
            org_id=org_id,
            resource_type="api_key",
            resource_id=str(key_id),
        )

    def rotate_api_key(
        self, user_id: uuid.UUID, org_id: uuid.UUID, key_id: uuid.UUID
    ) -> tuple[ApiKeyModel, str]:
        self.require_org_permission(user_id, org_id, Permission.APIKEY_MANAGE)
        old = self.repo.get_api_key(org_id, key_id)
        if old is None:
            raise NotFoundError("api key not found")
        old.revoked_at = utcnow()
        return self.create_api_key(user_id, org_id, old.name, list(old.scopes or []), None)

    def effective_permissions(self, role: OrgRole | None) -> frozenset[str]:
        if role is None:
            return frozenset()
        return frozenset(p.value for p in permissions_for(role))

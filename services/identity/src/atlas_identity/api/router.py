"""Identity HTTP routers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request

from atlas_identity.api.deps import CurrentUser, IdentitySvc, _client_ip, require_org_context
from atlas_identity.application.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    AuditLogResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    InviteMemberRequest,
    LoginRequest,
    MembershipResponse,
    OAuthProviderResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
    ProjectCreateRequest,
    ProjectMemberRequest,
    ProjectResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SwitchOrganizationRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from atlas_identity.application.service import RateLimitError
from atlas_identity.domain.rbac import Permission

auth_router = APIRouter(prefix="/auth", tags=["auth"])
orgs_router = APIRouter(prefix="/organizations", tags=["organizations"])
keys_router = APIRouter(prefix="/api-keys", tags=["api-keys"])
projects_router = APIRouter(prefix="/projects", tags=["projects"])


def _tokens(payload: dict[str, Any]) -> TokenResponse:
    return TokenResponse(**payload)


@auth_router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: RegisterRequest, request: Request, svc: IdentitySvc) -> TokenResponse:
    _user, _org, tokens = svc.register(
        email=str(body.email),
        password=body.password,
        full_name=body.full_name,
        organization_name=body.organization_name,
        ip=_client_ip(request),
        user_agent=request.headers.get("user-agent"),
    )
    return _tokens(tokens)


@auth_router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, svc: IdentitySvc) -> TokenResponse:
    redis = getattr(request.app.state.container, "redis", None)
    ip = _client_ip(request) or "unknown"
    if redis is not None:
        key = f"atlas:login:{ip}:{str(body.email).lower()}"
        try:
            count = int(redis.incr(key))
            if count == 1:
                redis.expire(key, 60)
            if count > 20:
                raise RateLimitError("too many login attempts")
        except RateLimitError:
            raise
        except Exception:  # noqa: BLE001
            pass
    return _tokens(
        svc.login(
            email=str(body.email),
            password=body.password,
            ip=_client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    )


@auth_router.post("/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, request: Request, svc: IdentitySvc) -> TokenResponse:
    return _tokens(svc.refresh(body.refresh_token, ip=_client_ip(request)))


@auth_router.post("/logout", status_code=204)
def logout(request: Request, ctx: CurrentUser, svc: IdentitySvc) -> None:
    if ctx.session_id is None:
        return
    svc.logout(ctx.session_id, ctx.user_id, ip=_client_ip(request))


@auth_router.get("/me", response_model=UserResponse)
def me(ctx: CurrentUser, svc: IdentitySvc) -> UserResponse:
    user = svc.repo.get_user(ctx.user_id)
    assert user is not None
    return UserResponse.model_validate(user)


@auth_router.patch("/me", response_model=UserResponse)
def update_me(body: UpdateProfileRequest, ctx: CurrentUser, svc: IdentitySvc) -> UserResponse:
    user = svc.repo.get_user(ctx.user_id)
    assert user is not None
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.active_organization_id is not None:
        svc.switch_organization(ctx.user_id, body.active_organization_id)
    svc.repo.session.flush()
    refreshed = svc.repo.get_user(ctx.user_id)
    assert refreshed is not None
    return UserResponse.model_validate(refreshed)


@auth_router.post("/change-password", status_code=204)
def change_password(
    body: ChangePasswordRequest, request: Request, ctx: CurrentUser, svc: IdentitySvc
) -> None:
    svc.change_password(
        ctx.user_id, body.current_password, body.new_password, ip=_client_ip(request)
    )


@auth_router.post("/forgot-password")
def forgot_password(body: ForgotPasswordRequest, svc: IdentitySvc) -> dict[str, str]:
    result = svc.forgot_password(str(body.email))
    return {"detail": result["detail"]}


@auth_router.post("/reset-password", status_code=204)
def reset_password(body: ResetPasswordRequest, svc: IdentitySvc) -> None:
    svc.reset_password(body.token, body.new_password)


@auth_router.get("/oauth/providers", response_model=OAuthProviderResponse)
def oauth_providers() -> OAuthProviderResponse:
    return OAuthProviderResponse(
        providers=["google", "github", "microsoft"],
        status="not_configured",
        detail="OIDC provider credentials are not configured. Hooks are ready for setup.",
    )


@orgs_router.post("", response_model=OrganizationResponse, status_code=201)
def create_org(
    body: OrganizationCreateRequest, ctx: CurrentUser, svc: IdentitySvc
) -> OrganizationResponse:
    org = svc.create_organization(ctx.user_id, body.name, body.slug)
    return OrganizationResponse.model_validate(org)


@orgs_router.get("", response_model=list[OrganizationResponse])
def list_orgs(ctx: CurrentUser, svc: IdentitySvc) -> list[OrganizationResponse]:
    orgs = svc.repo.list_organizations_for_user(ctx.user_id)
    return [OrganizationResponse.model_validate(o) for o in orgs]


@orgs_router.post("/switch", response_model=UserResponse)
def switch_org(body: SwitchOrganizationRequest, ctx: CurrentUser, svc: IdentitySvc) -> UserResponse:
    user = svc.switch_organization(ctx.user_id, body.organization_id)
    return UserResponse.model_validate(user)


@orgs_router.post("/{org_id}/invite", response_model=MembershipResponse, status_code=201)
def invite(
    org_id: UUID, body: InviteMemberRequest, ctx: CurrentUser, svc: IdentitySvc
) -> MembershipResponse:
    membership = svc.invite_member(ctx.user_id, org_id, str(body.email), body.role)
    return MembershipResponse(
        id=membership.id,
        user_id=membership.user_id,
        organization_id=membership.organization_id,
        role=membership.role,
        email=membership.invited_email,
    )


@orgs_router.get("/{org_id}/members", response_model=list[MembershipResponse])
def list_members(org_id: UUID, ctx: CurrentUser, svc: IdentitySvc) -> list[MembershipResponse]:
    svc.require_org_permission(ctx.user_id, org_id, Permission.ORG_READ)
    rows = svc.repo.list_memberships(org_id)
    out: list[MembershipResponse] = []
    for row in rows:
        user = svc.repo.get_user(row.user_id)
        out.append(
            MembershipResponse(
                id=row.id,
                user_id=row.user_id,
                organization_id=row.organization_id,
                role=row.role,
                email=user.email if user else row.invited_email,
            )
        )
    return out


@orgs_router.get("/{org_id}/audit", response_model=list[AuditLogResponse])
def list_audit(org_id: UUID, ctx: CurrentUser, svc: IdentitySvc) -> list[AuditLogResponse]:
    svc.require_org_permission(ctx.user_id, org_id, Permission.AUDIT_READ)
    rows = list(svc.repo.list_audit(org_id))
    return [
        AuditLogResponse(
            id=r.id,
            action=r.action,
            user_id=r.user_id,
            organization_id=r.organization_id,
            resource_type=r.resource_type,
            resource_id=r.resource_id,
            ip_address=r.ip_address,
            request_id=r.request_id,
            metadata=r.metadata_json or {},
            created_at=r.created_at,
        )
        for r in rows
    ]


@keys_router.post("", response_model=ApiKeyCreateResponse, status_code=201)
def create_api_key(
    body: ApiKeyCreateRequest, ctx: CurrentUser, svc: IdentitySvc
) -> ApiKeyCreateResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    key, raw = svc.create_api_key(
        ctx.user_id, ctx.organization_id, body.name, body.scopes, body.expires_in_days
    )
    return ApiKeyCreateResponse(
        id=key.id, name=key.name, prefix=key.prefix, api_key=raw, expires_at=key.expires_at
    )


@keys_router.get("", response_model=list[ApiKeyResponse])
def list_keys(ctx: CurrentUser, svc: IdentitySvc) -> list[ApiKeyResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.require_org_permission(ctx.user_id, ctx.organization_id, Permission.APIKEY_MANAGE)
    keys = svc.repo.list_api_keys(ctx.organization_id)
    return [
        ApiKeyResponse(
            id=k.id,
            name=k.name,
            prefix=k.prefix,
            scopes=list(k.scopes or []),
            last_used_at=k.last_used_at,
            expires_at=k.expires_at,
            created_at=k.created_at,
        )
        for k in keys
    ]


@keys_router.delete("/{key_id}", status_code=204)
def delete_key(key_id: UUID, ctx: CurrentUser, svc: IdentitySvc) -> None:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.revoke_api_key(ctx.user_id, ctx.organization_id, key_id)


@keys_router.post("/{key_id}/rotate", response_model=ApiKeyCreateResponse)
def rotate_key(key_id: UUID, ctx: CurrentUser, svc: IdentitySvc) -> ApiKeyCreateResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    key, raw = svc.rotate_api_key(ctx.user_id, ctx.organization_id, key_id)
    return ApiKeyCreateResponse(
        id=key.id, name=key.name, prefix=key.prefix, api_key=raw, expires_at=key.expires_at
    )


@projects_router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreateRequest, ctx: CurrentUser, svc: IdentitySvc
) -> ProjectResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    project = svc.create_project(
        ctx.user_id, ctx.organization_id, body.name, body.slug, body.description
    )
    return ProjectResponse.model_validate(project)


@projects_router.get("", response_model=list[ProjectResponse])
def list_projects(ctx: CurrentUser, svc: IdentitySvc) -> list[ProjectResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.require_org_permission(ctx.user_id, ctx.organization_id, Permission.PROJECT_READ)
    rows = list(svc.repo.session.scalars(svc.repo.tenant_projects(ctx.organization_id)))
    return [ProjectResponse.model_validate(p) for p in rows]


@projects_router.post("/{project_id}/members", status_code=201)
def add_project_member(
    project_id: UUID, body: ProjectMemberRequest, ctx: CurrentUser, svc: IdentitySvc
) -> dict[str, str]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.add_project_member(ctx.user_id, ctx.organization_id, project_id, body.user_id, body.role)
    return {"status": "ok"}


def build_identity_router() -> APIRouter:
    router = APIRouter()
    router.include_router(auth_router)
    router.include_router(orgs_router)
    router.include_router(keys_router)
    # Phase 3: project CRUD lives in atlas-catalog (/v1/projects).
    # identity.projects table retained for legacy RBAC membership rows.
    return router

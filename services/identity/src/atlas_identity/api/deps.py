"""FastAPI dependencies for identity."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Annotated

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy.orm import Session

from atlas_identity.application.service import AuthError, ForbiddenError, IdentityService
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.context import AuthContext, set_auth_context
from atlas_identity.infrastructure.repository import IdentityRepository, ensure_aware, utcnow
from atlas_identity.infrastructure.security import TokenSettings, decode_access_token, hash_token

_bearer = HTTPBearer(auto_error=False)


def get_db_session(request: Request) -> Generator[Session, None, None]:
    factory = request.app.state.container.session_factory
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_token_settings(request: Request) -> TokenSettings:
    settings = request.app.state.settings
    return TokenSettings(
        secret_key=settings.atlas_secret_key,
        access_token_minutes=getattr(settings, "atlas_access_token_minutes", 15),
        refresh_token_days=getattr(settings, "atlas_refresh_token_days", 14),
    )


def get_identity_service(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    tokens: Annotated[TokenSettings, Depends(get_token_settings)],
) -> IdentityService:
    return IdentityService(IdentityRepository(session), tokens)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


def resolve_principal(
    request: Request,
    session: Annotated[Session, Depends(get_db_session)],
    tokens: Annotated[TokenSettings, Depends(get_token_settings)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> AuthContext:
    """Authenticate via JWT Bearer or X-API-Key and bind tenant context."""
    repo = IdentityRepository(session)
    if x_api_key:
        key = repo.get_api_key_by_hash(hash_token(x_api_key))
        if key is None or key.revoked_at is not None:
            raise AuthError("invalid api key")
        if key.expires_at is not None and ensure_aware(key.expires_at) < utcnow():
            raise AuthError("api key expired")
        key.last_used_at = utcnow()
        user = repo.get_user(key.user_id)
        if user is None or not user.is_active:
            raise AuthError("user inactive")
        membership = repo.get_membership(key.organization_id, user.id)
        role = OrgRole(membership.role) if membership else None
        svc = IdentityService(repo, tokens)
        ctx = AuthContext(
            user_id=user.id,
            email=user.email,
            organization_id=key.organization_id,
            role=role,
            session_id=None,
            auth_method="api_key",
            permissions=svc.effective_permissions(role),
        )
        set_auth_context(ctx)
        request.state.auth = ctx
        return ctx

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AuthError("authentication required")
    try:
        claims = decode_access_token(tokens, credentials.credentials)
    except PyJWTError as exc:
        raise AuthError("invalid access token") from exc
    session_row = repo.get_session(claims.session_id)
    if session_row is None or session_row.revoked_at is not None:
        raise AuthError("session revoked")
    user = repo.get_user(claims.sub)
    if user is None or not user.is_active:
        raise AuthError("user inactive")
    role = OrgRole(claims.role) if claims.role else None
    svc = IdentityService(repo, tokens)
    ctx = AuthContext(
        user_id=user.id,
        email=user.email,
        organization_id=claims.org_id,
        role=role,
        session_id=claims.session_id,
        auth_method="jwt",
        permissions=svc.effective_permissions(role),
    )
    set_auth_context(ctx)
    request.state.auth = ctx
    return ctx


def require_permission(permission: Permission) -> Callable[..., AuthContext]:
    def _dep(ctx: Annotated[AuthContext, Depends(resolve_principal)]) -> AuthContext:
        if ctx.role is None or not has_permission(ctx.role, permission):
            raise ForbiddenError(f"missing permission {permission}")
        if ctx.organization_id is None:
            raise ForbiddenError("organization context required")
        return ctx

    return _dep


def require_org_context(ctx: Annotated[AuthContext, Depends(resolve_principal)]) -> AuthContext:
    if ctx.organization_id is None:
        raise ForbiddenError("organization context required")
    return ctx


CurrentUser = Annotated[AuthContext, Depends(resolve_principal)]
DbSession = Annotated[Session, Depends(get_db_session)]
IdentitySvc = Annotated[IdentityService, Depends(get_identity_service)]

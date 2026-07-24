"""Tenant / auth request context (ContextVars)."""

from __future__ import annotations

import uuid
from contextvars import ContextVar
from dataclasses import dataclass

from atlas_identity.domain.rbac import OrgRole


@dataclass
class AuthContext:
    """Authenticated principal for the current request."""

    user_id: uuid.UUID
    email: str
    organization_id: uuid.UUID | None
    role: OrgRole | None
    session_id: uuid.UUID | None
    auth_method: str  # jwt | api_key
    permissions: frozenset[str]


_auth_ctx: ContextVar[AuthContext | None] = ContextVar("atlas_auth_context", default=None)


def set_auth_context(ctx: AuthContext | None) -> None:
    """Bind auth context for the current request."""
    _auth_ctx.set(ctx)


def get_auth_context() -> AuthContext | None:
    """Return the bound auth context, if any."""
    return _auth_ctx.get()


def require_auth_context() -> AuthContext:
    """Return auth context or raise PermissionError."""
    ctx = get_auth_context()
    if ctx is None:
        raise PermissionError("authentication required")
    return ctx

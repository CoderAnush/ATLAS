"""JWT access tokens and opaque refresh-token helpers."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt


@dataclass(frozen=True)
class TokenSettings:
    """JWT timing and signing configuration."""

    secret_key: str
    algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    issuer: str = "atlas"


@dataclass(frozen=True)
class AccessTokenClaims:
    """Decoded access-token claims used by auth middleware."""

    sub: uuid.UUID
    org_id: uuid.UUID | None
    session_id: uuid.UUID
    role: str | None
    token_type: str = "access"


def _now() -> datetime:
    return datetime.now(UTC)


def hash_token(raw: str) -> str:
    """Return a SHA-256 hex digest for storing opaque tokens."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_refresh_token() -> str:
    """Generate a high-entropy opaque refresh token."""
    return secrets.token_urlsafe(48)


def create_access_token(
    *,
    settings: TokenSettings,
    user_id: uuid.UUID,
    session_id: uuid.UUID,
    org_id: uuid.UUID | None,
    role: str | None,
    extra: dict[str, Any] | None = None,
) -> tuple[str, datetime]:
    """Create a signed JWT access token and its expiry."""
    expires = _now() + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "sid": str(session_id),
        "org": str(org_id) if org_id else None,
        "role": role,
        "type": "access",
        "iss": settings.issuer,
        "iat": int(_now().timestamp()),
        "exp": int(expires.timestamp()),
        "jti": str(uuid.uuid4()),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires


def decode_access_token(settings: TokenSettings, token: str) -> AccessTokenClaims:
    """Validate and decode an access token."""
    payload = jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.algorithm],
        issuer=settings.issuer,
        options={"require": ["exp", "sub", "type", "sid"]},
    )
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("not an access token")
    org_raw = payload.get("org")
    return AccessTokenClaims(
        sub=uuid.UUID(payload["sub"]),
        org_id=uuid.UUID(org_raw) if org_raw else None,
        session_id=uuid.UUID(payload["sid"]),
        role=payload.get("role"),
        token_type="access",
    )


def new_api_key_material() -> tuple[str, str, str]:
    """Return (prefix, raw_key, key_hash) for a new API key."""
    prefix = f"atk_{secrets.token_hex(3)}"
    secret = secrets.token_urlsafe(32)
    raw = f"{prefix}.{secret}"
    return prefix, raw, hash_token(raw)

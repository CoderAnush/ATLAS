# Identity Service

Bounded context for authentication, organizations, RBAC, API keys, sessions, and audit logging.

## Layout

```text
domain/           RBAC roles & permissions
application/      Use cases + schemas
infrastructure/   SQLAlchemy models, JWT, Argon2, repositories
api/              FastAPI routers & dependencies
```

Mounted by `apps/api` under `/v1/auth`, `/v1/organizations`, `/v1/api-keys`, `/v1/projects`.

## Auth

- Access: JWT (short-lived)
- Refresh: opaque token, hashed at rest, rotated on use
- Passwords: Argon2
- API keys: `atk_…` prefix, SHA-256 hashed, optional expiry; `X-API-Key` header

## Tenancy

Principal carries `organization_id`. Repositories filter by org. Switch via `POST /v1/organizations/switch`.

## Roles

`owner > admin > ml_engineer > data_scientist > approver > viewer`

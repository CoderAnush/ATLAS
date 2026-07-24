"""Identity domain enums and role/permission vocabulary."""

from __future__ import annotations

from enum import StrEnum


class OrgRole(StrEnum):
    """Organization-scoped RBAC roles (hierarchy: owner > admin > ... > viewer)."""

    OWNER = "owner"
    ADMIN = "admin"
    ML_ENGINEER = "ml_engineer"
    DATA_SCIENTIST = "data_scientist"
    APPROVER = "approver"
    VIEWER = "viewer"


class Permission(StrEnum):
    """Fine-grained permissions evaluated by middleware and use cases."""

    ORG_READ = "org:read"
    ORG_WRITE = "org:write"
    ORG_MANAGE_MEMBERS = "org:manage_members"
    ORG_MANAGE_ROLES = "org:manage_roles"
    ORG_BILLING = "org:billing"

    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    PROJECT_MANAGE_MEMBERS = "project:manage_members"

    USER_INVITE = "user:invite"
    APIKEY_MANAGE = "apikey:manage"
    AUDIT_READ = "audit:read"
    SETTINGS_WRITE = "settings:write"


# Higher index = higher privilege for hierarchy comparisons.
ROLE_RANK: dict[OrgRole, int] = {
    OrgRole.VIEWER: 10,
    OrgRole.APPROVER: 20,
    OrgRole.DATA_SCIENTIST: 30,
    OrgRole.ML_ENGINEER: 40,
    OrgRole.ADMIN: 50,
    OrgRole.OWNER: 60,
}

ROLE_PERMISSIONS: dict[OrgRole, frozenset[Permission]] = {
    OrgRole.VIEWER: frozenset(
        {
            Permission.ORG_READ,
            Permission.PROJECT_READ,
            Permission.AUDIT_READ,
        }
    ),
    OrgRole.APPROVER: frozenset(
        {
            Permission.ORG_READ,
            Permission.PROJECT_READ,
            Permission.AUDIT_READ,
        }
    ),
    OrgRole.DATA_SCIENTIST: frozenset(
        {
            Permission.ORG_READ,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.AUDIT_READ,
        }
    ),
    OrgRole.ML_ENGINEER: frozenset(
        {
            Permission.ORG_READ,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_DELETE,
            Permission.AUDIT_READ,
            Permission.APIKEY_MANAGE,
        }
    ),
    OrgRole.ADMIN: frozenset(
        {
            Permission.ORG_READ,
            Permission.ORG_WRITE,
            Permission.ORG_MANAGE_MEMBERS,
            Permission.ORG_MANAGE_ROLES,
            Permission.PROJECT_READ,
            Permission.PROJECT_WRITE,
            Permission.PROJECT_DELETE,
            Permission.PROJECT_MANAGE_MEMBERS,
            Permission.USER_INVITE,
            Permission.APIKEY_MANAGE,
            Permission.AUDIT_READ,
            Permission.SETTINGS_WRITE,
        }
    ),
    OrgRole.OWNER: frozenset(set(Permission)),
}


def role_at_least(role: OrgRole, minimum: OrgRole) -> bool:
    """Return True when ``role`` is at least as privileged as ``minimum``."""
    return ROLE_RANK[role] >= ROLE_RANK[minimum]


def permissions_for(role: OrgRole) -> frozenset[Permission]:
    """Return the permission set granted by an organization role."""
    return ROLE_PERMISSIONS[role]


def has_permission(role: OrgRole, permission: Permission) -> bool:
    """Return True when the role includes the permission."""
    return permission in ROLE_PERMISSIONS[role]

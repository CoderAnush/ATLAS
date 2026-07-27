"""Identity / auth / tenancy tests using SQLite with schema translation."""

from __future__ import annotations

import uuid

import pytest
from atlas_api.app import create_app
from atlas_api.config import Settings
from atlas_catalog.infrastructure import models as _catalog_models  # noqa: F401
from atlas_db.base import Base
from atlas_db.session import create_session_factory
from atlas_feature_store.infrastructure import models as _feature_store_models  # noqa: F401
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure import models as _models  # noqa: F401
from atlas_preparation.infrastructure import models as _prep_models  # noqa: F401
from atlas_profiling.infrastructure import models as _profiling_models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    # Map schemas onto SQLite default; skip identity.projects* (catalog owns projects).
    with engine.begin() as conn:
        conn_ex = conn.execution_options(
            schema_translate_map={
                "identity": None,
                "catalog": None,
                "profiling": None,
                "preparation": None,
                "feature_store": None,
            }
        )
        tables = [
            t
            for t in Base.metadata.sorted_tables
            if not (t.schema == "identity" and t.name in {"projects", "project_memberships"})
        ]
        Base.metadata.create_all(conn_ex, tables=tables)
    yield engine
    engine.dispose()


@pytest.fixture()
def client(engine) -> TestClient:
    settings = Settings(
        atlas_env="testing",
        atlas_secret_key="test-secret-key-for-jwt-signing-phase2",
        atlas_json_logs=False,
        database_url="sqlite+pysqlite:///:memory:",
    )
    app = create_app(settings)
    app.state.container.engine = engine
    factory = create_session_factory(engine)

    def _factory():  # type: ignore[no-untyped-def]
        session = factory()
        session.connection(
            execution_options={
                "schema_translate_map": {
                    "identity": None,
                    "catalog": None,
                    "profiling": None,
                    "preparation": None,
                    "feature_store": None,
                }
            }
        )
        return session

    app.state.container.session_factory = _factory  # type: ignore[assignment]

    class _Redis:
        def __init__(self) -> None:
            self._data: dict[str, int] = {}

        def incr(self, key: str) -> int:
            self._data[key] = self._data.get(key, 0) + 1
            return self._data[key]

        def expire(self, key: str, _: int) -> None:
            return None

        def close(self) -> None:
            return None

    app.state.container.redis = _Redis()  # type: ignore[assignment]
    with TestClient(app) as test_client:
        yield test_client


def _register(client: TestClient, suffix: str | None = None) -> dict:
    suffix = suffix or uuid.uuid4().hex[:8]
    payload = {
        "email": f"user_{suffix}@example.com",
        "password": "Str0ng!Pass",
        "full_name": "Test User",
        "organization_name": f"Acme {suffix}",
    }
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    data["_email"] = payload["email"]
    data["_password"] = payload["password"]
    return data


def test_rbac_hierarchy() -> None:
    assert has_permission(OrgRole.OWNER, Permission.ORG_BILLING)
    assert has_permission(OrgRole.ADMIN, Permission.ORG_MANAGE_MEMBERS)
    assert not has_permission(OrgRole.VIEWER, Permission.APIKEY_MANAGE)


def test_register_login_me(client: TestClient) -> None:
    tokens = _register(client)
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = client.get("/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"].endswith("@example.com")

    login = client.post(
        "/v1/auth/login",
        json={"email": tokens["_email"], "password": tokens["_password"]},
    )
    assert login.status_code == 200
    assert "access_token" in login.json()


def test_refresh_and_logout(client: TestClient) -> None:
    tokens = _register(client)
    refreshed = client.post("/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    login = client.post(
        "/v1/auth/login",
        json={"email": tokens["_email"], "password": tokens["_password"]},
    )
    rt = login.json()["refresh_token"]
    client.post(
        "/v1/auth/logout",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    bad = client.post("/v1/auth/refresh", json={"refresh_token": rt})
    assert bad.status_code == 401


def test_tenant_isolation(client: TestClient) -> None:
    a = _register(client, "tenant_a")
    b = _register(client, "tenant_b")
    ha = {"Authorization": f"Bearer {a['access_token']}"}
    hb = {"Authorization": f"Bearer {b['access_token']}"}
    pa = client.post("/v1/projects", headers=ha, json={"name": "Proj A", "slug": "proj-a"})
    assert pa.status_code == 201, pa.text
    projects_b = client.get("/v1/projects", headers=hb)
    assert projects_b.status_code == 200
    assert projects_b.json() == []


def test_api_keys(client: TestClient) -> None:
    tokens = _register(client, "keys")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    created = client.post("/v1/api-keys", headers=headers, json={"name": "ci", "scopes": ["read"]})
    assert created.status_code == 201, created.text
    raw = created.json()["api_key"]
    assert raw.startswith("atk_")
    listed = client.get("/v1/api-keys", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    key_id = listed.json()[0]["id"]
    me = client.get("/v1/auth/me", headers={"X-API-Key": raw})
    assert me.status_code == 200
    assert client.delete(f"/v1/api-keys/{key_id}", headers=headers).status_code == 204
    assert client.get("/v1/auth/me", headers={"X-API-Key": raw}).status_code == 401


def test_invite_member(client: TestClient) -> None:
    owner = _register(client, "ownerperm")
    headers = {"Authorization": f"Bearer {owner['access_token']}"}
    orgs = client.get("/v1/organizations", headers=headers).json()
    org_id = orgs[0]["id"]
    invite = client.post(
        f"/v1/organizations/{org_id}/invite",
        headers=headers,
        json={"email": "viewer_perm@example.com", "role": "viewer"},
    )
    assert invite.status_code == 201, invite.text


def test_api_key_rotate(client: TestClient) -> None:
    tokens = _register(client, "rotate")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    created = client.post("/v1/api-keys", headers=headers, json={"name": "ci", "scopes": ["read"]})
    assert created.status_code == 201
    key_id = created.json()["id"]
    old = created.json()["api_key"]
    rotated = client.post(f"/v1/api-keys/{key_id}/rotate", headers=headers)
    assert rotated.status_code == 200, rotated.text
    new = rotated.json()["api_key"]
    assert new != old
    assert client.get("/v1/auth/me", headers={"X-API-Key": old}).status_code == 401
    assert client.get("/v1/auth/me", headers={"X-API-Key": new}).status_code == 200


def test_viewer_cannot_create_api_key(client: TestClient) -> None:
    owner = _register(client, "ownerview")
    viewer = _register(client, "viewonly")
    oh = {"Authorization": f"Bearer {owner['access_token']}"}
    vh = {"Authorization": f"Bearer {viewer['access_token']}"}
    org_id = client.get("/v1/organizations", headers=oh).json()[0]["id"]
    invite = client.post(
        f"/v1/organizations/{org_id}/invite",
        headers=oh,
        json={"email": viewer["_email"], "role": "viewer"},
    )
    assert invite.status_code == 201, invite.text
    switched = client.post(
        "/v1/organizations/switch",
        headers=vh,
        json={"organization_id": org_id},
    )
    assert switched.status_code in (200, 204), switched.text
    # Re-login so access token carries active org (if JWT embeds org)
    login = client.post(
        "/v1/auth/login",
        json={"email": viewer["_email"], "password": viewer["_password"]},
    )
    assert login.status_code == 200
    vh2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
    denied = client.post("/v1/api-keys", headers=vh2, json={"name": "nope", "scopes": ["read"]})
    assert denied.status_code == 403


def test_change_password(client: TestClient) -> None:
    tokens = _register(client, "chpass")
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    assert (
        client.post(
            "/v1/auth/change-password",
            headers=headers,
            json={"current_password": tokens["_password"], "new_password": "N3w!Passw0rd"},
        ).status_code
        == 204
    )
    assert (
        client.post(
            "/v1/auth/login",
            json={"email": tokens["_email"], "password": tokens["_password"]},
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/v1/auth/login",
            json={"email": tokens["_email"], "password": "N3w!Passw0rd"},
        ).status_code
        == 200
    )


def test_unauthenticated_me(client: TestClient) -> None:
    assert client.get("/v1/auth/me").status_code == 401

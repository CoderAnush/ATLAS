"""Catalog API integration tests (SQLite + fake object storage)."""

from __future__ import annotations

import io
import uuid
from datetime import timedelta
from typing import BinaryIO

import pytest
from atlas_api.app import create_app
from atlas_api.config import Settings
from atlas_catalog.infrastructure import models as _catalog_models  # noqa: F401
from atlas_db.base import Base
from atlas_db.session import create_session_factory
from atlas_identity.infrastructure import models as _identity_models  # noqa: F401
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(
        self, bucket: str, object_name: str, data: bytes, *, content_type: str | None = None
    ) -> None:
        self.objects[f"{bucket}/{object_name}"] = data

    def upload_stream(
        self,
        bucket: str,
        object_name: str,
        stream: BinaryIO,
        length: int,
        *,
        content_type: str | None = None,
        part_size: int = 10 * 1024 * 1024,
    ) -> None:
        self.objects[f"{bucket}/{object_name}"] = stream.read(length)

    def download(self, bucket: str, object_name: str) -> bytes:
        return self.objects[f"{bucket}/{object_name}"]

    def delete(self, bucket: str, object_name: str) -> None:
        self.objects.pop(f"{bucket}/{object_name}", None)

    def presigned_url(
        self, bucket: str, object_name: str, *, expires: timedelta | None = None
    ) -> str:
        return f"https://minio.local/{bucket}/{object_name}?sig=test"


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

    with engine.begin() as conn:
        conn_ex = conn.execution_options(
            schema_translate_map={"identity": None, "catalog": None, "profiling": None}
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
        atlas_secret_key="test-secret-key-for-jwt-signing-phase3",
        atlas_json_logs=False,
        database_url="sqlite+pysqlite:///:memory:",
        atlas_max_upload_bytes=5_000_000,
    )
    app = create_app(settings)
    app.state.container.engine = engine
    factory = create_session_factory(engine)

    def _factory():  # type: ignore[no-untyped-def]
        session = factory()
        session.connection(
            execution_options={
                "schema_translate_map": {"identity": None, "catalog": None, "profiling": None}
            }
        )
        return session

    app.state.container.session_factory = _factory  # type: ignore[assignment]
    app.state.container.storage = FakeStorage()  # type: ignore[assignment]

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


def _auth(client: TestClient, suffix: str | None = None) -> dict:
    suffix = suffix or uuid.uuid4().hex[:8]
    payload = {
        "email": f"cat_{suffix}@example.com",
        "password": "Str0ng!Pass",
        "full_name": "Catalog User",
        "organization_name": f"Org {suffix}",
    }
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    data["_headers"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data


def test_project_crud_and_dataset_upload(client: TestClient) -> None:
    auth = _auth(client, "p1")
    h = auth["_headers"]
    project = client.post(
        "/v1/projects",
        headers=h,
        json={"name": "Demo", "description": "d", "tags": ["ml"]},
    )
    assert project.status_code == 201, project.text
    pid = project.json()["id"]
    assert client.get(f"/v1/projects/{pid}", headers=h).status_code == 200

    csv_bytes = b"a,b\n1,2\n3,4\n"
    upload = client.post(
        "/v1/datasets/upload",
        headers=h,
        data={"project_id": pid, "name": "demo-csv", "tags": "raw,v1"},
        files={"file": ("demo.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["status"] == "ready"
    assert body["current_version"] == 1
    did = body["id"]

    # version 2
    csv2 = b"a,b\n1,2\n3,4\n5,6\n"
    upload2 = client.post(
        "/v1/datasets/upload",
        headers=h,
        data={"project_id": pid, "dataset_id": did},
        files={"file": ("demo.csv", io.BytesIO(csv2), "text/csv")},
    )
    assert upload2.status_code == 201, upload2.text
    assert upload2.json()["current_version"] == 2

    versions = client.get(f"/v1/datasets/{did}/versions", headers=h)
    assert versions.status_code == 200
    assert len(versions.json()) == 2

    meta = client.get(f"/v1/datasets/{did}/metadata", headers=h)
    assert meta.status_code == 200
    assert meta.json()["statistics"]["row_estimate"] == 3

    dl = client.post(f"/v1/datasets/{did}/download", headers=h)
    assert dl.status_code == 200
    assert "url" in dl.json()

    fav = client.post(f"/v1/datasets/{did}/favorite", headers=h)
    assert fav.status_code == 200 and fav.json()["favorite"] is True

    listed = client.get("/v1/datasets/search", headers=h, params={"q": "demo"})
    assert listed.status_code == 200
    assert listed.json()["total"] >= 1

    assert client.post(f"/v1/datasets/{did}/archive", headers=h).status_code == 200
    assert client.post(f"/v1/datasets/{did}/restore", headers=h).status_code == 200
    assert client.delete(f"/v1/datasets/{did}", headers=h).status_code == 204


def test_tenant_isolation_datasets(client: TestClient) -> None:
    a = _auth(client, "ta")
    b = _auth(client, "tb")
    pa = client.post("/v1/projects", headers=a["_headers"], json={"name": "A"}).json()
    csv_bytes = b"x\n1\n"
    up = client.post(
        "/v1/datasets/upload",
        headers=a["_headers"],
        data={"project_id": pa["id"]},
        files={"file": ("a.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert up.status_code == 201
    did = up.json()["id"]
    assert client.get(f"/v1/datasets/{did}", headers=b["_headers"]).status_code == 404
    assert client.get("/v1/datasets", headers=b["_headers"]).json()["total"] == 0


def test_rejects_bad_extension(client: TestClient) -> None:
    auth = _auth(client, "bad")
    h = auth["_headers"]
    pid = client.post("/v1/projects", headers=h, json={"name": "P"}).json()["id"]
    bad = client.post(
        "/v1/datasets/upload",
        headers=h,
        data={"project_id": pid},
        files={"file": ("evil.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
    )
    assert bad.status_code == 400


def test_duplicate_checksum(client: TestClient) -> None:
    auth = _auth(client, "dup")
    h = auth["_headers"]
    pid = client.post("/v1/projects", headers=h, json={"name": "P"}).json()["id"]
    payload = b"a,b\n1,2\n"
    assert (
        client.post(
            "/v1/datasets/upload",
            headers=h,
            data={"project_id": pid},
            files={"file": ("one.csv", io.BytesIO(payload), "text/csv")},
        ).status_code
        == 201
    )
    dup = client.post(
        "/v1/datasets/upload",
        headers=h,
        data={"project_id": pid},
        files={"file": ("two.csv", io.BytesIO(payload), "text/csv")},
    )
    assert dup.status_code == 409


def test_connector_stub(client: TestClient) -> None:
    auth = _auth(client, "conn")
    h = auth["_headers"]
    resp = client.post(
        "/v1/connectors",
        headers=h,
        json={"name": "warehouse", "connector_type": "sql", "config": {"host": "db"}},
    )
    assert resp.status_code == 201
    assert resp.json()["connector_type"] == "sql"

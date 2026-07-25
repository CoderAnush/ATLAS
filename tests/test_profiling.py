"""Profiling API integration tests."""

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
from atlas_profiling.infrastructure import models as _profiling_models  # noqa: F401
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
        atlas_secret_key="test-secret-key-for-jwt-signing-phase4",
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
        def incr(self, key: str) -> int:
            return 1

        def expire(self, key: str, _: int) -> None:
            return None

        def close(self) -> None:
            return None

    app.state.container.redis = _Redis()  # type: ignore[assignment]
    with TestClient(app) as test_client:
        yield test_client


def _auth(client: TestClient) -> dict:
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"prof_{suffix}@example.com",
        "password": "Str0ng!Pass",
        "full_name": "Profiler",
        "organization_name": f"Org {suffix}",
    }
    response = client.post("/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    data = response.json()
    data["_headers"] = {"Authorization": f"Bearer {data['access_token']}"}
    return data


def test_profiling_run_and_summary(client: TestClient) -> None:
    auth = _auth(client)
    h = auth["_headers"]
    pid = client.post("/v1/projects", headers=h, json={"name": "P"}).json()["id"]
    csv_bytes = b"id,age,salary,survived\n1,20,30000,0\n2,30,40000,1\n3,40,50000,0\n4,25,35000,1\n"
    up = client.post(
        "/v1/datasets/upload",
        headers=h,
        data={"project_id": pid, "name": "titanic-mini"},
        files={"file": ("t.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert up.status_code == 201, up.text
    did = up.json()["id"]

    run = client.post(f"/v1/profiling/run/{did}", headers=h)
    assert run.status_code == 202, run.text
    job_id = run.json()["job_id"]

    job = client.get(f"/v1/profiling/jobs/{job_id}", headers=h)
    assert job.status_code == 200
    assert job.json()["status"] == "completed"

    summary = client.get(f"/v1/profiling/{did}/summary", headers=h)
    assert summary.status_code == 200, summary.text
    body = summary.json()
    assert body["rows"] == 4
    assert body["quality_overall"] > 0
    assert "summary" in body

    quality = client.get(f"/v1/profiling/{did}/quality", headers=h)
    assert quality.status_code == 200
    stats = client.get(f"/v1/profiling/{did}/statistics", headers=h)
    assert stats.status_code == 200
    assert isinstance(stats.json(), list)
    profile = client.get(f"/v1/profiling/{did}", headers=h)
    assert profile.status_code == 200
    assert "columns" in profile.json()

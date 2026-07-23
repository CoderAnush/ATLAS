"""API smoke tests that do not require live infrastructure."""

from unittest.mock import MagicMock

from atlas_api.app import create_app
from atlas_api.config import Settings
from atlas_api.di.container import AppContainer
from fastapi.testclient import TestClient


def _settings() -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        atlas_env="testing",
        atlas_json_logs=False,
        otel_traces_enabled=False,
        postgres_host="localhost",
        redis_url="redis://localhost:6379/0",
        minio_endpoint="localhost:9000",
        mlflow_tracking_uri="http://localhost:5000",
    )


def test_health_live_with_mocked_container(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = _settings()

    fake_engine = MagicMock()
    fake_redis = MagicMock()
    fake_redis.ping.return_value = True
    fake_minio = MagicMock()
    fake_minio.list_buckets.return_value = []
    fake_minio.bucket_exists.return_value = True

    container = AppContainer(
        settings=settings,
        engine=fake_engine,
        session_factory=MagicMock(),
        redis=fake_redis,
        storage=MagicMock(),
        minio_client=fake_minio,
    )

    def fake_build(_settings: Settings) -> AppContainer:
        return container

    monkeypatch.setattr("atlas_api.app.build_container", fake_build)
    monkeypatch.setattr("atlas_api.api.v1.health.check_database", lambda _engine: True)
    monkeypatch.setattr("atlas_api.api.v1.health.check_minio", lambda _client: True)

    app = create_app(settings)
    client = TestClient(app)
    response = client.get("/health/live")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "X-Request-ID" in response.headers


def test_root_endpoint(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = _settings()
    container = AppContainer(
        settings=settings,
        engine=MagicMock(),
        session_factory=MagicMock(),
        redis=MagicMock(),
        storage=MagicMock(),
        minio_client=MagicMock(),
    )
    container.minio_client.bucket_exists.return_value = True
    monkeypatch.setattr("atlas_api.app.build_container", lambda _s: container)
    app = create_app(settings)
    client = TestClient(app)
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["name"] == "ATLAS API"

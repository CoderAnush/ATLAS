"""Configuration unit tests."""

from atlas_api.config import Settings


def test_settings_defaults() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        atlas_env="testing",
        atlas_cors_origins="http://localhost:3000",
    )
    assert settings.atlas_service_name == "atlas-api"
    assert "localhost:3000" in settings.cors_origins[0]
    assert settings.sqlalchemy_database_url.startswith("postgresql+psycopg://")


def test_database_url_override() -> None:
    settings = Settings(
        _env_file=None,  # type: ignore[call-arg]
        database_url="postgresql+psycopg://u:p@db:5432/atlas",
    )
    assert settings.sqlalchemy_database_url == "postgresql+psycopg://u:p@db:5432/atlas"

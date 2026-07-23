"""Centralized application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the ATLAS API and shared platform services."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    atlas_env: Literal["development", "testing", "production"] = "development"
    atlas_log_level: str = "INFO"
    atlas_json_logs: bool = True
    atlas_service_name: str = "atlas-api"
    atlas_api_host: str = "0.0.0.0"
    atlas_api_port: int = 8000
    atlas_secret_key: str = Field(default="change-me-in-production")
    atlas_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "atlas"
    postgres_user: str = "atlas"
    postgres_password: str = "atlas"
    database_url: str | None = None

    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "atlas"
    minio_secure: bool = False

    mlflow_tracking_uri: str = "http://localhost:5000"

    otel_exporter_otlp_endpoint: str | None = None
    otel_traces_enabled: bool = False

    @property
    def cors_origins(self) -> list[str]:
        """Parse CORS origins from a comma-separated environment value."""
        return [origin.strip() for origin in self.atlas_cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Build a SQLAlchemy URL, preferring an explicit DATABASE_URL override."""
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def is_testing(self) -> bool:
        """Return True when running in the testing environment."""
        return self.atlas_env == "testing"


@lru_cache
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()

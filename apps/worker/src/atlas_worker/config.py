"""Worker settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    """Configuration for Celery workers."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    atlas_env: Literal["development", "testing", "production"] = "development"
    atlas_log_level: str = "INFO"
    atlas_json_logs: bool = True
    atlas_service_name: str = "atlas-worker"
    redis_url: str = "redis://localhost:6379/0"
    celery_task_always_eager: bool = False


@lru_cache
def get_worker_settings() -> WorkerSettings:
    """Return cached worker settings."""
    return WorkerSettings()

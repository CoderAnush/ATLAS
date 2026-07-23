"""Object storage health-check utilities."""

from atlas_core.errors import DependencyError
from minio import Minio


def check_minio(client: Minio) -> bool:
    """Verify MinIO connectivity, raising a dependency error on failure."""
    try:
        client.list_buckets()
    except Exception as exc:
        raise DependencyError("MinIO connectivity check failed.") from exc
    return True

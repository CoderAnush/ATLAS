"""MinIO implementation of the ATLAS object-storage port."""

from datetime import timedelta
from io import BytesIO
from typing import BinaryIO

from minio import Minio


class MinioObjectStorage:
    """Object storage adapter backed by a MinIO-compatible server."""

    def __init__(self, client: Minio) -> None:
        """Initialize the adapter with a configured MinIO client."""
        self._client = client

    def upload(
        self, bucket: str, object_name: str, data: bytes, *, content_type: str | None = None
    ) -> None:
        """Store bytes in MinIO."""
        self.upload_stream(
            bucket,
            object_name,
            BytesIO(data),
            length=len(data),
            content_type=content_type,
        )

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
        """Stream bytes into MinIO using multipart when length warrants it."""
        self._client.put_object(
            bucket,
            object_name,
            stream,
            length=length,
            part_size=part_size,
            content_type=content_type or "application/octet-stream",
        )

    def download(self, bucket: str, object_name: str) -> bytes:
        """Download an object and close the underlying HTTP response."""
        response = self._client.get_object(bucket, object_name)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def delete(self, bucket: str, object_name: str) -> None:
        """Remove an object from MinIO."""
        self._client.remove_object(bucket, object_name)

    def presigned_url(
        self, bucket: str, object_name: str, *, expires: timedelta | None = None
    ) -> str:
        """Create a temporary download URL for an object."""
        return self._client.presigned_get_object(
            bucket,
            object_name,
            expires=expires or timedelta(hours=1),
        )

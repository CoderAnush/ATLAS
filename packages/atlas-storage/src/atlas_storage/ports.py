"""Ports defining the object-storage boundary."""

from datetime import timedelta
from typing import Protocol, runtime_checkable


@runtime_checkable
class ObjectStorage(Protocol):
    """Minimal object storage interface used by ATLAS application code."""

    def upload(
        self, bucket: str, object_name: str, data: bytes, *, content_type: str | None = None
    ) -> None:
        """Store bytes at the requested bucket and object path."""

    def download(self, bucket: str, object_name: str) -> bytes:
        """Return the complete stored object as bytes."""

    def delete(self, bucket: str, object_name: str) -> None:
        """Remove a stored object."""

    def presigned_url(
        self, bucket: str, object_name: str, *, expires: timedelta | None = None
    ) -> str:
        """Return a temporary URL for downloading an object."""

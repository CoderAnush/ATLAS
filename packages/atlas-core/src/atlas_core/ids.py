"""Identifier generation utilities."""

from __future__ import annotations

import secrets
import time
import uuid
from uuid import uuid4


def new_id() -> str:
    """Return a collision-resistant UUID4 identifier as a string."""
    return str(uuid4())


def uuid7() -> uuid.UUID:
    """Generate an RFC 9562 UUIDv7 (time-ordered) for primary keys."""
    # Prefer stdlib when available (Python 3.13+).
    factory = getattr(uuid, "uuid7", None)
    if callable(factory):
        return factory()  # type: ignore[no-any-return]

    unix_ts_ms = int(time.time() * 1000) & ((1 << 48) - 1)
    rand_a = secrets.randbits(12)
    rand_b = secrets.randbits(62)
    value = (unix_ts_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0b10 << 62) | rand_b
    return uuid.UUID(int=value)


def new_uuid7_str() -> str:
    """Return a UUIDv7 as a string."""
    return str(uuid7())

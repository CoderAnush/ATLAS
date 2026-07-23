"""Identifier generation utilities."""

from uuid import uuid4


def new_id() -> str:
    """Return a collision-resistant UUID4 identifier as a string."""
    return str(uuid4())

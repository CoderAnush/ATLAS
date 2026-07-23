"""Database infrastructure package for ATLAS."""

from atlas_db.base import Base
from atlas_db.session import create_engine_from_url, create_session_factory, session_scope

__all__ = ["Base", "create_engine_from_url", "create_session_factory", "session_scope"]
"""atlas-db package (placeholder)."""

__version__ = "0.0.0"

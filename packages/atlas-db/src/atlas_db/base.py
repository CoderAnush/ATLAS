"""SQLAlchemy declarative base for ATLAS persistence models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ATLAS SQLAlchemy ORM models."""

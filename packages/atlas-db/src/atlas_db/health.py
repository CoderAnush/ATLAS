"""Database health-check utilities."""

from atlas_core.errors import DependencyError
from sqlalchemy import Engine, text


def check_database(engine: Engine) -> bool:
    """Verify database connectivity, raising a dependency error on failure."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:
        raise DependencyError("Database connectivity check failed.") from exc
    return True

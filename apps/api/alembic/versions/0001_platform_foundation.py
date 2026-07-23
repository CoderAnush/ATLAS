"""Initial Alembic revision — platform foundation (no domain tables yet)."""

from __future__ import annotations

from collections.abc import Sequence

revision: str = "0001_platform_foundation"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No domain tables in Phase 1 — migration chain established only."""
    pass


def downgrade() -> None:
    """No-op downgrade for the empty foundation revision."""
    pass

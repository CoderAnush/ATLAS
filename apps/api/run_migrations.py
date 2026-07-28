#!/usr/bin/env python
"""Run Alembic migrations (used inside Compose / local uv)."""

from __future__ import annotations

import atlas_catalog.infrastructure.models  # noqa: F401
import atlas_experiments.infrastructure.models  # noqa: F401
import atlas_feature_store.infrastructure.models  # noqa: F401
import atlas_hpo.infrastructure.models  # noqa: F401
import atlas_identity.infrastructure.models  # noqa: F401
import atlas_modeling.infrastructure.models  # noqa: F401
import atlas_preparation.infrastructure.models  # noqa: F401
import atlas_profiling.infrastructure.models  # noqa: F401
from alembic import command
from alembic.config import Config


def main() -> None:
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    print("alembic upgrade head: ok")


if __name__ == "__main__":
    main()

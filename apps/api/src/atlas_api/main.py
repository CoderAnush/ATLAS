"""Uvicorn entrypoint for the ATLAS API."""

from __future__ import annotations

import uvicorn

from atlas_api.app import create_app
from atlas_api.config import get_settings

app = create_app()


def run() -> None:
    """Run the API server using settings defaults."""
    settings = get_settings()
    uvicorn.run(
        "atlas_api.main:app",
        host=settings.atlas_api_host,
        port=settings.atlas_api_port,
        reload=False,
    )


if __name__ == "__main__":
    run()

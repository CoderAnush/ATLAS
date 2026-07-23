"""CLI entry for starting the Celery worker."""

from __future__ import annotations

from atlas_worker.celery_app import celery_app


def main() -> None:
    """Start a Celery worker process."""
    celery_app.worker_main(
        argv=[
            "worker",
            "--loglevel=INFO",
            "--concurrency=2",
            "-Q",
            "celery",
        ]
    )


if __name__ == "__main__":
    main()

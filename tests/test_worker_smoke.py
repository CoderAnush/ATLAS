"""Worker foundation smoke tests."""

from atlas_worker.tasks.heartbeat import heartbeat


def test_heartbeat_task(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "true")
    result = heartbeat()
    assert result["status"] == "ok"
    assert result["service"] == "atlas-worker"

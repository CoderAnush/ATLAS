"""Unit tests for experiment registry, leaderboard, and comparison."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from typing import Any

import atlas_experiments.infrastructure.models  # noqa: F401
import atlas_identity.infrastructure.models  # noqa: F401
import pytest
from atlas_core.ids import uuid7
from atlas_db.base import Base
from atlas_experiments.application.ports import NoOpExperimentTracker
from atlas_experiments.application.service import ExperimentsService
from atlas_experiments.infrastructure.repository import ExperimentRepository
from atlas_identity.domain.rbac import OrgRole
from atlas_identity.infrastructure.models import MembershipModel, OrganizationModel, UserModel
from atlas_identity.infrastructure.repository import IdentityRepository
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


class FakeStorage:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def upload(self, bucket: str, key: str, data: bytes, content_type: str | None = None) -> None:
        self.objects[f"{bucket}/{key}"] = data

    def upload_stream(self, *args: Any, **kwargs: Any) -> None:
        return None

    def download(self, bucket: str, key: str) -> bytes:
        return self.objects[f"{bucket}/{key}"]

    def delete(self, bucket: str, key: str) -> None:
        self.objects.pop(f"{bucket}/{key}", None)

    def exists(self, bucket: str, key: str) -> bool:
        return f"{bucket}/{key}" in self.objects

    def presigned_url(self, bucket: str, key: str, expires: Any = None) -> str:
        return f"https://example.test/{bucket}/{key}"


SCHEMA_MAP = {"identity": None, "experiments": None}


@pytest.fixture()
def session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [
        table
        for table in Base.metadata.tables.values()
        if table.schema in {"identity", "experiments", None}
        and table.name
        in {
            "users",
            "organizations",
            "memberships",
            "experiments",
            "experiment_runs",
            "experiment_metrics",
            "experiment_artifacts",
            "experiment_parameters",
            "experiment_environment",
            "experiment_tags",
            "experiment_notes",
            "experiment_lineage",
            "experiment_comparisons",
            "leaderboard_entries",
            "experiment_favorites",
            "experiment_history",
        }
    ]
    with engine.begin() as conn:
        conn_ex = conn.execution_options(schema_translate_map=SCHEMA_MAP)
        Base.metadata.create_all(conn_ex, tables=tables)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    sess = factory()
    sess.connection(execution_options={"schema_translate_map": SCHEMA_MAP})
    yield sess
    sess.close()


def _seed_identity(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    org_id = uuid7()
    user_id = uuid7()
    session.add(OrganizationModel(id=org_id, name="Org", slug=f"org-{org_id.hex[:8]}"))
    session.add(
        UserModel(
            id=user_id,
            email=f"{user_id.hex[:8]}@example.com",
            full_name="Tester",
            password_hash="x",
        )
    )
    session.add(
        MembershipModel(
            organization_id=org_id,
            user_id=user_id,
            role=OrgRole.OWNER.value,
        )
    )
    session.flush()
    return org_id, user_id


def _service(session: Session) -> ExperimentsService:
    return ExperimentsService(
        ExperimentRepository(session),
        IdentityRepository(session),
        FakeStorage(),
        NoOpExperimentTracker(),
        bucket="atlas",
    )


def test_record_training_run_creates_experiment_and_leaderboard(session: Session) -> None:
    org_id, user_id = _seed_identity(session)
    svc = _service(session)
    run = svc.record_training_run(
        {
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "training_job_id": uuid7(),
            "dataset_id": uuid7(),
            "dataset_version": 1,
            "feature_set_id": uuid7(),
            "algorithm": "random_forest",
            "problem_type": "binary_classification",
            "metrics": {"accuracy": 0.9, "precision": 0.8, "recall": 0.7, "f1": 0.75},
            "hyperparameters": {"n_estimators": 100},
            "config": {"random_seed": 42},
            "runtime_seconds": 1.5,
            "primary_metric": "accuracy",
        }
    )
    assert run.status == "completed"
    assert run.primary_metric_value == 0.9
    board = svc.leaderboard(user_id, org_id)
    assert len(board) == 1
    assert board[0].accuracy == 0.9
    experiments = svc.list_experiments(user_id, org_id)
    assert len(experiments) == 1
    assert experiments[0].run_count == 1


def test_compare_runs_highlights_best(session: Session) -> None:
    org_id, user_id = _seed_identity(session)
    svc = _service(session)
    run_a = svc.record_training_run(
        {
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "training_job_id": uuid7(),
            "algorithm": "logistic_regression",
            "metrics": {"accuracy": 0.6, "f1": 0.5},
            "config": {},
            "primary_metric": "accuracy",
            "runtime_seconds": 2.0,
        }
    )
    run_b = svc.record_training_run(
        {
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "training_job_id": uuid7(),
            "algorithm": "random_forest",
            "metrics": {"accuracy": 0.95, "f1": 0.9},
            "config": {},
            "primary_metric": "accuracy",
            "runtime_seconds": 3.0,
        }
    )
    comparison = svc.compare_runs(user_id, org_id, [run_a.id, run_b.id], "cmp")
    assert comparison.result_json["best_run_id"] == str(run_b.id)
    assert "accuracy" in comparison.result_json["best_by_metric"]


def test_clone_and_search(session: Session) -> None:
    org_id, user_id = _seed_identity(session)
    svc = _service(session)
    run = svc.record_training_run(
        {
            "organization_id": org_id,
            "created_by_user_id": user_id,
            "training_job_id": uuid7(),
            "algorithm": "svm",
            "experiment_name": "svm-baseline",
            "metrics": {"accuracy": 0.7},
            "config": {},
        }
    )
    clone = svc.clone_experiment(user_id, org_id, run.experiment_id, "svm-baseline-clone")
    assert clone.name == "svm-baseline-clone"
    found = svc.search(user_id, org_id, {"query": "svm", "limit": 10})
    assert any(item.id == run.experiment_id for item in found)

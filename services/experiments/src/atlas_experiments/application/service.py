"""Experiment application service."""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import sys
import uuid
from datetime import timedelta
from typing import Any

from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_storage.ports import ObjectStorage

from atlas_experiments.application.ports import ExperimentTracker, TrackerLogRequest
from atlas_experiments.domain import ArtifactKind, ExperimentStatus, RunSource, RunStatus
from atlas_experiments.infrastructure.models import (
    ExperimentArtifactModel,
    ExperimentComparisonModel,
    ExperimentEnvironmentModel,
    ExperimentFavoriteModel,
    ExperimentHistoryModel,
    ExperimentLineageModel,
    ExperimentMetricModel,
    ExperimentModel,
    ExperimentParameterModel,
    ExperimentRunModel,
    ExperimentTagModel,
    LeaderboardEntryModel,
)
from atlas_experiments.infrastructure.repository import ExperimentRepository, utcnow

logger = logging.getLogger("atlas.experiments")

ATLAS_VERSION = "0.9.0"


class ExperimentsService:
    """Registry, leaderboard, comparison, and automatic run recording."""

    def __init__(
        self,
        repo: ExperimentRepository,
        identity: IdentityRepository,
        storage: ObjectStorage,
        tracker: ExperimentTracker,
        *,
        bucket: str,
    ) -> None:
        self.repo = repo
        self.identity = identity
        self.storage = storage
        self.tracker = tracker
        self.bucket = bucket

    def _require(self, user_id: uuid.UUID, org_id: uuid.UUID, permission: Permission) -> None:
        membership = self.identity.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        if not has_permission(OrgRole(membership.role), permission):
            raise ForbiddenError(f"missing permission {permission.value}")

    def _history(
        self,
        *,
        org_id: uuid.UUID,
        experiment_id: uuid.UUID,
        event: str,
        message: str = "",
        run_id: uuid.UUID | None = None,
        actor: uuid.UUID | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self.repo.add_history(
            ExperimentHistoryModel(
                organization_id=org_id,
                experiment_id=experiment_id,
                run_id=run_id,
                event=event,
                message=message,
                actor_user_id=actor,
                extra_json=extra or {},
            )
        )

    def list_experiments(
        self, user_id: uuid.UUID, org_id: uuid.UUID, *, limit: int = 100
    ) -> list[ExperimentModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_experiments(org_id, limit=limit)

    def get_experiment(
        self, user_id: uuid.UUID, org_id: uuid.UUID, experiment_id: uuid.UUID
    ) -> ExperimentModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        row = self.repo.get_experiment(org_id, experiment_id)
        if row is None:
            raise NotFoundError("experiment not found")
        return row

    def list_runs(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        experiment_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[ExperimentRunModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_runs(org_id, experiment_id=experiment_id, limit=limit)

    def get_run(
        self, user_id: uuid.UUID, org_id: uuid.UUID, run_id: uuid.UUID
    ) -> ExperimentRunModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        row = self.repo.get_run(org_id, run_id)
        if row is None:
            raise NotFoundError("experiment run not found")
        return row

    def search(
        self, user_id: uuid.UUID, org_id: uuid.UUID, body: dict[str, Any]
    ) -> list[ExperimentModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.search_experiments(
            org_id,
            query=str(body.get("query") or ""),
            algorithm=body.get("algorithm"),
            status=body.get("status"),
            tag=body.get("tag"),
            owner_id=body.get("owner_id"),
            dataset_id=body.get("dataset_id"),
            limit=int(body.get("limit") or 50),
        )

    def leaderboard(
        self, user_id: uuid.UUID, org_id: uuid.UUID, *, limit: int = 100
    ) -> list[LeaderboardEntryModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_leaderboard(org_id, limit=limit)

    def compare_runs(
        self, user_id: uuid.UUID, org_id: uuid.UUID, run_ids: list[uuid.UUID], name: str
    ) -> ExperimentComparisonModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        runs = []
        for run_id in run_ids:
            run = self.repo.get_run(org_id, run_id)
            if run is None:
                raise NotFoundError(f"run not found: {run_id}")
            runs.append(run)

        metrics_keys = sorted({k for run in runs for k in (run.metrics_json or {})})
        best_by_metric: dict[str, Any] = {}
        for key in metrics_keys:
            scored = [
                (run.id, float(run.metrics_json[key]))
                for run in runs
                if key in run.metrics_json and isinstance(run.metrics_json[key], (int, float))
            ]
            if not scored:
                continue
            # Prefer higher for common maximize metrics
            maximize = key.lower() not in {"mae", "mse", "rmse", "mape", "loss", "log_loss"}
            winner = (
                max(scored, key=lambda item: item[1])
                if maximize
                else min(scored, key=lambda item: item[1])
            )
            best_by_metric[key] = {
                "run_id": str(winner[0]),
                "value": winner[1],
                "maximize": maximize,
            }

        best_run = max(
            runs,
            key=lambda r: float(r.primary_metric_value or float("-inf")),
        )
        result = {
            "runs": [
                {
                    "id": str(run.id),
                    "name": run.name,
                    "algorithm": run.algorithm,
                    "dataset_version": run.dataset_version,
                    "feature_set_id": str(run.feature_set_id) if run.feature_set_id else None,
                    "runtime_seconds": run.runtime_seconds,
                    "metrics": run.metrics_json,
                    "hyperparameters": run.hyperparameters_json,
                    "primary_metric": run.primary_metric,
                    "primary_metric_value": run.primary_metric_value,
                }
                for run in runs
            ],
            "best_run_id": str(best_run.id),
            "best_by_metric": best_by_metric,
            "visualizations": {
                "scatter": [
                    {
                        "run_id": str(run.id),
                        "x": run.runtime_seconds or 0,
                        "y": run.primary_metric_value or 0,
                        "label": run.algorithm or run.name,
                    }
                    for run in runs
                ],
                "bar_metrics": {
                    key: [
                        {
                            "run_id": str(run.id),
                            "value": float(run.metrics_json.get(key) or 0),
                        }
                        for run in runs
                    ]
                    for key in metrics_keys[:8]
                },
                "parallel_coordinates": {"placeholder": True},
            },
        }
        comparison = ExperimentComparisonModel(
            organization_id=org_id,
            name=name or "comparison",
            run_ids_json=[str(r) for r in run_ids],
            result_json=result,
            created_by_user_id=user_id,
        )
        self.repo.add_comparison(comparison)
        self.repo.session.flush()
        return comparison

    def favorite_run(
        self, user_id: uuid.UUID, org_id: uuid.UUID, run_id: uuid.UUID
    ) -> ExperimentRunModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        run = self.repo.get_run(org_id, run_id)
        if run is None:
            raise NotFoundError("experiment run not found")
        run.favorite = True
        self.repo.add_favorite(
            ExperimentFavoriteModel(
                organization_id=org_id,
                user_id=user_id,
                experiment_id=run.experiment_id,
                run_id=run.id,
            )
        )
        self._history(
            org_id=org_id,
            experiment_id=run.experiment_id,
            run_id=run.id,
            event="RunFavorited",
            actor=user_id,
        )
        self.repo.session.flush()
        return run

    def archive(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        *,
        experiment_id: uuid.UUID | None = None,
        run_id: uuid.UUID | None = None,
    ) -> dict[str, str]:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        if run_id is not None:
            run = self.repo.get_run(org_id, run_id)
            if run is None:
                raise NotFoundError("experiment run not found")
            run.archived = True
            run.status = RunStatus.ARCHIVED.value
            self._history(
                org_id=org_id,
                experiment_id=run.experiment_id,
                run_id=run.id,
                event="RunArchived",
                actor=user_id,
            )
            self.repo.session.flush()
            return {"status": "archived", "run_id": str(run.id)}
        if experiment_id is not None:
            experiment = self.repo.get_experiment(org_id, experiment_id)
            if experiment is None:
                raise NotFoundError("experiment not found")
            experiment.status = ExperimentStatus.ARCHIVED.value
            self._history(
                org_id=org_id,
                experiment_id=experiment.id,
                event="ExperimentArchived",
                actor=user_id,
            )
            self.repo.session.flush()
            return {"status": "archived", "experiment_id": str(experiment.id)}
        raise ForbiddenError("experiment_id or run_id required")

    def clone_experiment(
        self, user_id: uuid.UUID, org_id: uuid.UUID, experiment_id: uuid.UUID, name: str | None
    ) -> ExperimentModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        source = self.repo.get_experiment(org_id, experiment_id)
        if source is None:
            raise NotFoundError("experiment not found")
        clone = ExperimentModel(
            organization_id=org_id,
            name=name or f"{source.name} (clone)",
            description=source.description,
            status=ExperimentStatus.ACTIVE.value,
            group_name=source.group_name,
            dataset_id=source.dataset_id,
            feature_set_id=source.feature_set_id,
            algorithm=source.algorithm,
            problem_type=source.problem_type,
            created_by_user_id=user_id,
            metadata_json={
                **(source.metadata_json or {}),
                "cloned_from": str(source.id),
            },
        )
        self.repo.add_experiment(clone)
        for tag in self.repo.list_tags(org_id, source.id):
            self.repo.add_tag(
                ExperimentTagModel(
                    organization_id=org_id,
                    experiment_id=clone.id,
                    tag_key=tag.tag_key,
                    tag_value=tag.tag_value,
                )
            )
        self._history(
            org_id=org_id,
            experiment_id=clone.id,
            event="ExperimentCreated",
            message=f"cloned from {source.id}",
            actor=user_id,
        )
        self.repo.session.flush()
        return clone

    def export_experiment(
        self, user_id: uuid.UUID, org_id: uuid.UUID, experiment_id: uuid.UUID
    ) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        experiment = self.repo.get_experiment(org_id, experiment_id)
        if experiment is None:
            raise NotFoundError("experiment not found")
        runs = self.repo.list_runs(org_id, experiment_id=experiment_id, limit=500)
        payload = {
            "experiment": {
                "id": str(experiment.id),
                "name": experiment.name,
                "description": experiment.description,
                "algorithm": experiment.algorithm,
                "best_metric_name": experiment.best_metric_name,
                "best_metric_value": experiment.best_metric_value,
            },
            "runs": [
                {
                    "id": str(run.id),
                    "name": run.name,
                    "status": run.status,
                    "metrics": run.metrics_json,
                    "hyperparameters": run.hyperparameters_json,
                    "reproducibility": run.reproducibility_json,
                }
                for run in runs
            ],
            "history": [
                {"event": h.event, "message": h.message, "created_at": h.created_at.isoformat()}
                for h in self.repo.list_history(org_id, experiment_id)
            ],
        }
        raw = json.dumps(payload, indent=2, default=str).encode()
        key = f"{org_id}/experiments/{experiment_id}/export.json"
        self.storage.upload(self.bucket, key, raw, content_type="application/json")
        url = self.storage.presigned_url(self.bucket, key, expires=timedelta(hours=1))
        return {"storage_key": key, "download_url": url, "size_bytes": len(raw)}

    def get_run_detail(
        self, user_id: uuid.UUID, org_id: uuid.UUID, run_id: uuid.UUID
    ) -> dict[str, Any]:
        run = self.get_run(user_id, org_id, run_id)
        return {
            "run": run,
            "metrics": self.repo.list_metrics(org_id, run_id),
            "artifacts": self.repo.list_artifacts(org_id, run_id),
            "history": self.repo.list_history(org_id, run.experiment_id),
        }

    def record_training_run(self, payload: dict[str, Any]) -> ExperimentRunModel:
        """Called automatically by ModelingService after a training job completes."""
        org_id = uuid.UUID(str(payload["organization_id"]))
        user_id = uuid.UUID(str(payload["created_by_user_id"]))
        training_job_id = uuid.UUID(str(payload["training_job_id"]))
        existing = self.repo.get_run_by_training_job(org_id, training_job_id)
        if existing is not None:
            return existing

        algorithm = str(payload.get("algorithm") or "unknown")
        name = str(payload.get("experiment_name") or f"train_{algorithm}")
        experiment = ExperimentModel(
            organization_id=org_id,
            name=name,
            description=str(payload.get("summary") or "Training experiment"),
            status=ExperimentStatus.ACTIVE.value,
            group_name=str(payload.get("group_name") or "training"),
            dataset_id=_maybe_uuid(payload.get("dataset_id")),
            feature_set_id=_maybe_uuid(payload.get("feature_set_id")),
            algorithm=algorithm,
            problem_type=payload.get("problem_type"),
            created_by_user_id=user_id,
            metadata_json={"source": RunSource.TRAINING.value},
        )
        self.repo.add_experiment(experiment)
        logger.info(
            "ExperimentCreated",
            extra={"tenant_id": str(org_id), "experiment_id": str(experiment.id)},
        )
        self._history(
            org_id=org_id,
            experiment_id=experiment.id,
            event="ExperimentCreated",
            message="training experiment created",
            actor=user_id,
        )

        return self._persist_run(
            experiment=experiment,
            payload=payload,
            source=RunSource.TRAINING,
            name=str(payload.get("run_name") or f"run_{training_job_id.hex[:8]}"),
        )

    def record_hpo_run(self, payload: dict[str, Any]) -> ExperimentRunModel:
        """Called automatically by HpoService after an optimization study completes."""
        org_id = uuid.UUID(str(payload["organization_id"]))
        user_id = uuid.UUID(str(payload["created_by_user_id"]))
        study_id = uuid.UUID(str(payload["hpo_study_id"]))
        existing = self.repo.get_run_by_hpo_study(org_id, study_id)
        if existing is not None:
            return existing

        algorithm = str(payload.get("algorithm") or "unknown")
        name = str(payload.get("experiment_name") or f"hpo_{algorithm}")
        experiment = ExperimentModel(
            organization_id=org_id,
            name=name,
            description=str(payload.get("summary") or "HPO experiment"),
            status=ExperimentStatus.ACTIVE.value,
            group_name=str(payload.get("group_name") or "hpo"),
            dataset_id=_maybe_uuid(payload.get("dataset_id")),
            feature_set_id=_maybe_uuid(payload.get("feature_set_id")),
            algorithm=algorithm,
            problem_type=payload.get("problem_type"),
            created_by_user_id=user_id,
            metadata_json={"source": RunSource.HPO.value},
        )
        self.repo.add_experiment(experiment)
        logger.info(
            "ExperimentCreated",
            extra={"tenant_id": str(org_id), "experiment_id": str(experiment.id)},
        )
        self._history(
            org_id=org_id,
            experiment_id=experiment.id,
            event="ExperimentCreated",
            message="hpo experiment created",
            actor=user_id,
        )
        return self._persist_run(
            experiment=experiment,
            payload=payload,
            source=RunSource.HPO,
            name=str(payload.get("run_name") or f"hpo_{study_id.hex[:8]}"),
        )

    def _persist_run(
        self,
        *,
        experiment: ExperimentModel,
        payload: dict[str, Any],
        source: RunSource,
        name: str,
    ) -> ExperimentRunModel:
        org_id = experiment.organization_id
        user_id = experiment.created_by_user_id
        metrics = dict(payload.get("metrics") or {})
        params = dict(payload.get("hyperparameters") or payload.get("params") or {})
        config = dict(payload.get("config") or {})
        primary_metric = str(payload.get("primary_metric") or _default_metric(metrics))
        primary_value = _as_float(metrics.get(primary_metric))
        runtime = _as_float(payload.get("runtime_seconds"))

        logger.info(
            "RunStarted", extra={"tenant_id": str(org_id), "experiment_id": str(experiment.id)}
        )

        environment = {
            "python_version": sys.version.split()[0],
            "os_name": platform.platform(),
            "hardware": payload.get("hardware")
            or {"cpu": platform.processor() or "unknown", "gpu": "placeholder"},
            "library_versions": payload.get("library_versions")
            or {
                "atlas": ATLAS_VERSION,
                "python": sys.version.split()[0],
            },
        }
        reproducibility = {
            "random_seed": payload.get("random_seed"),
            "git_commit": payload.get("git_commit") or "",
            "atlas_version": ATLAS_VERSION,
            "config_hash": hashlib.sha256(
                json.dumps(config, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "metrics_hash": hashlib.sha256(
                json.dumps(metrics, sort_keys=True, default=str).encode()
            ).hexdigest(),
            "environment": environment,
        }

        visualizations = {
            "metric_history": [
                {"step": 0, "metric": key, "value": float(value)}
                for key, value in metrics.items()
                if isinstance(value, (int, float))
            ],
            "accuracy_timeline": [{"step": 0, "value": float(metrics["accuracy"])}]
            if isinstance(metrics.get("accuracy"), (int, float))
            else [],
            "loss_timeline": [
                {"step": 0, "value": float(metrics.get("loss") or metrics.get("mae") or 0)}
            ]
            if any(k in metrics for k in ("loss", "mae", "rmse"))
            else [],
            "scatter": {
                "x": runtime or 0,
                "y": primary_value or 0,
                "label": experiment.algorithm or name,
            },
            "bar_charts": {
                key: float(value)
                for key, value in metrics.items()
                if isinstance(value, (int, float))
            },
            "parallel_coordinates": {"placeholder": True},
            "confusion_matrix": {"placeholder": True, "data": metrics.get("confusion_matrix")},
            "roc": {"placeholder": True},
            "precision_recall": {"placeholder": True},
        }

        run = ExperimentRunModel(
            organization_id=org_id,
            experiment_id=experiment.id,
            name=name,
            status=RunStatus.COMPLETED.value,
            source=source.value,
            training_job_id=_maybe_uuid(payload.get("training_job_id")),
            hpo_job_id=_maybe_uuid(payload.get("hpo_job_id")),
            hpo_study_id=_maybe_uuid(payload.get("hpo_study_id")),
            dataset_id=_maybe_uuid(payload.get("dataset_id")),
            dataset_version=payload.get("dataset_version"),
            feature_set_id=_maybe_uuid(payload.get("feature_set_id")),
            algorithm=experiment.algorithm,
            problem_type=experiment.problem_type,
            random_seed=payload.get("random_seed"),
            git_commit=payload.get("git_commit"),
            atlas_version=ATLAS_VERSION,
            primary_metric=primary_metric,
            primary_metric_value=primary_value,
            runtime_seconds=runtime,
            config_json=config,
            hyperparameters_json=params,
            metrics_json=metrics,
            reproducibility_json=reproducibility,
            visualizations_json=visualizations,
            created_by_user_id=user_id,
            started_at=utcnow(),
            completed_at=utcnow(),
        )
        self.repo.add_run(run)
        logger.info("RunCompleted", extra={"tenant_id": str(org_id), "run_id": str(run.id)})

        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                self.repo.add_metric(
                    ExperimentMetricModel(
                        organization_id=org_id,
                        experiment_id=experiment.id,
                        run_id=run.id,
                        metric_name=str(key),
                        metric_value=float(value),
                        step=0,
                        split="validation",
                    )
                )
                logger.info("MetricStored", extra={"metric": key, "run_id": str(run.id)})

        for key, value in {**params, **config}.items():
            self.repo.add_parameter(
                ExperimentParameterModel(
                    organization_id=org_id,
                    experiment_id=experiment.id,
                    run_id=run.id,
                    param_key=str(key)[:255],
                    param_value=str(value)[:4000],
                )
            )

        self.repo.add_environment(
            ExperimentEnvironmentModel(
                organization_id=org_id,
                experiment_id=experiment.id,
                run_id=run.id,
                python_version=environment["python_version"],
                os_name=environment["os_name"],
                hardware_json=environment["hardware"],
                library_versions_json=environment["library_versions"],
            )
        )

        self.repo.add_lineage(
            ExperimentLineageModel(
                organization_id=org_id,
                experiment_id=experiment.id,
                run_id=run.id,
                dataset_id=run.dataset_id,
                dataset_version=run.dataset_version,
                feature_set_id=run.feature_set_id,
                training_job_id=run.training_job_id,
                hpo_job_id=run.hpo_job_id,
                hpo_study_id=run.hpo_study_id,
                detail_json={"source": source.value},
            )
        )

        self.repo.add_tag(
            ExperimentTagModel(
                organization_id=org_id,
                experiment_id=experiment.id,
                tag_key="source",
                tag_value=source.value,
            )
        )
        if experiment.algorithm:
            self.repo.add_tag(
                ExperimentTagModel(
                    organization_id=org_id,
                    experiment_id=experiment.id,
                    tag_key="algorithm",
                    tag_value=experiment.algorithm,
                )
            )

        artifact_prefix = f"{org_id}/experiments/{experiment.id}/runs/{run.id}"
        artifact_specs: list[tuple[str, str, bytes]] = [
            (
                ArtifactKind.METRICS_JSON.value,
                "metrics.json",
                json.dumps(metrics, default=str).encode(),
            ),
            (
                ArtifactKind.TRAINING_CONFIG.value,
                "config.json",
                json.dumps(config, default=str).encode(),
            ),
            (
                ArtifactKind.REPRODUCIBILITY.value,
                "reproducibility.json",
                json.dumps(reproducibility, default=str).encode(),
            ),
            (
                ArtifactKind.LOGS.value,
                "run.log",
                f"Experiment run {run.id} completed via {source.value}\n".encode(),
            ),
        ]
        report = payload.get("report")
        if report is not None:
            artifact_specs.append(
                (
                    ArtifactKind.TRAINING_REPORT.value,
                    "report.json",
                    json.dumps(report, default=str).encode(),
                )
            )
        schema = payload.get("feature_schema")
        if schema is not None:
            artifact_specs.append(
                (
                    ArtifactKind.FEATURE_SCHEMA.value,
                    "feature_schema.json",
                    json.dumps(schema, default=str).encode(),
                )
            )
        pipeline = payload.get("pipeline")
        if pipeline is not None:
            artifact_specs.append(
                (
                    ArtifactKind.PIPELINE_JSON.value,
                    "pipeline.json",
                    json.dumps(pipeline, default=str).encode(),
                )
            )
        for kind in (
            ArtifactKind.CONFUSION_MATRIX,
            ArtifactKind.ROC,
            ArtifactKind.PRECISION_RECALL,
        ):
            artifact_specs.append(
                (
                    kind.value,
                    f"{kind.value}.json",
                    json.dumps({"placeholder": True}, default=str).encode(),
                )
            )

        model_bytes = payload.get("model_bytes")
        if isinstance(model_bytes, (bytes, bytearray)):
            artifact_specs.append((ArtifactKind.MODEL.value, "model.pkl", bytes(model_bytes)))

        for artifact_type, filename, content in artifact_specs:
            key = f"{artifact_prefix}/{filename}"
            self.storage.upload(self.bucket, key, content, content_type="application/octet-stream")
            checksum = hashlib.sha256(content).hexdigest()
            self.repo.add_artifact(
                ExperimentArtifactModel(
                    organization_id=org_id,
                    experiment_id=experiment.id,
                    run_id=run.id,
                    artifact_type=artifact_type,
                    name=filename,
                    storage_key=key,
                    content_type="application/json"
                    if filename.endswith(".json")
                    else "application/octet-stream",
                    size_bytes=len(content),
                    checksum_sha256=checksum,
                )
            )
            logger.info("ArtifactStored", extra={"artifact": filename, "run_id": str(run.id)})

        entry = LeaderboardEntryModel(
            organization_id=org_id,
            experiment_id=experiment.id,
            run_id=run.id,
            algorithm=run.algorithm,
            accuracy=_as_float(metrics.get("accuracy")),
            precision=_as_float(metrics.get("precision")),
            recall=_as_float(metrics.get("recall")),
            f1=_as_float(metrics.get("f1")),
            loss=_as_float(metrics.get("loss") or metrics.get("mae") or metrics.get("rmse")),
            runtime_seconds=runtime,
            rank_score=primary_value,
        )
        self.repo.add_leaderboard(entry)
        logger.info("LeaderboardUpdated", extra={"run_id": str(run.id)})

        experiment.run_count = int(experiment.run_count or 0) + 1
        if primary_value is not None and (
            experiment.best_metric_value is None
            or primary_value >= float(experiment.best_metric_value)
        ):
            experiment.best_run_id = run.id
            experiment.best_metric_name = primary_metric
            experiment.best_metric_value = primary_value

        handle = self.tracker.start_run(
            TrackerLogRequest(
                experiment_name=f"atlas/{org_id}/{experiment.name}",
                run_name=run.name,
                params={str(k): v for k, v in params.items()},
                metrics={k: float(v) for k, v in metrics.items() if isinstance(v, (int, float))},
                tags={"source": source.value, "atlas_version": ATLAS_VERSION},
                artifacts={
                    "metrics.json": json.dumps(metrics, default=str).encode(),
                    "reproducibility.json": json.dumps(reproducibility, default=str).encode(),
                },
            )
        )
        run.mlflow_run_id = handle.run_id
        self.tracker.end_run(handle.run_id)

        self._history(
            org_id=org_id,
            experiment_id=experiment.id,
            run_id=run.id,
            event="RunCompleted",
            message=f"{source.value} run recorded",
            actor=user_id,
            extra={"primary_metric": primary_metric, "primary_metric_value": primary_value},
        )
        self.repo.session.flush()
        return run


def _maybe_uuid(value: Any) -> uuid.UUID | None:
    if value is None or value == "":
        return None
    return uuid.UUID(str(value))


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _default_metric(metrics: dict[str, Any]) -> str:
    for key in ("accuracy", "f1", "r2", "roc_auc", "mae", "rmse"):
        if key in metrics:
            return key
    return next(iter(metrics), "score")

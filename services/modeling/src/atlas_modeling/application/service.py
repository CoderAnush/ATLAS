"""Modeling application service with HITL approval."""

from __future__ import annotations

import hashlib
import io
import json
import uuid
from datetime import timedelta
from typing import Any

import pandas as pd
from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_feature_store.domain import FeatureSetStatus
from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_profiling.infrastructure.repository import ProfilingRepository
from atlas_storage.ports import ObjectStorage
from sqlalchemy import select

from atlas_modeling.domain import JobStatus, ModelStatus, ProblemType
from atlas_modeling.infrastructure.engine import run_training
from atlas_modeling.infrastructure.models import (
    ModelVersionModel,
    TrainedModelModel,
    TrainingArtifactModel,
    TrainingConfigModel,
    TrainingJobModel,
    TrainingLineageModel,
    TrainingLogModel,
    TrainingMetricModel,
)
from atlas_modeling.infrastructure.repository import ModelingRepository, utcnow


class ModelingService:
    def __init__(
        self,
        repo: ModelingRepository,
        catalog: CatalogRepository,
        features: FeatureStoreRepository,
        identity: IdentityRepository,
        profiling: ProfilingRepository,
        storage: ObjectStorage,
        *,
        bucket: str,
    ) -> None:
        self.repo = repo
        self.catalog = catalog
        self.features = features
        self.identity = identity
        self.profiling = profiling
        self.storage = storage
        self.bucket = bucket

    def _require(self, user_id: uuid.UUID, org_id: uuid.UUID, permission: Permission) -> None:
        membership = self.identity.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        if not has_permission(OrgRole(membership.role), permission):
            raise ForbiddenError(f"missing permission {permission.value}")

    def enqueue(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        feature_set_id: uuid.UUID,
        config: dict[str, Any],
    ) -> TrainingJobModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        feature_set = self.features.get_feature_set(org_id, feature_set_id)
        if feature_set is None:
            raise NotFoundError("feature set not found")
        if feature_set.status != FeatureSetStatus.MATERIALIZED.value:
            raise ForbiddenError("only materialized feature sets can be trained")
        if not feature_set.matrix_storage_key:
            raise ForbiddenError("feature matrix artifact is missing")

        dataset = self.catalog.get_dataset(org_id, feature_set.dataset_id)
        if dataset is None:
            raise NotFoundError("dataset not found")

        job = TrainingJobModel(
            organization_id=org_id,
            feature_set_id=feature_set_id,
            dataset_id=feature_set.dataset_id,
            dataset_version=feature_set.output_dataset_version or dataset.current_version,
            status=JobStatus.QUEUED.value,
            progress=0,
            config_json=config,
            created_by_user_id=user_id,
        )
        self.repo.add_job(job)
        self.repo.add_config(
            TrainingConfigModel(organization_id=org_id, job_id=job.id, config_json=dict(config))
        )
        self.repo.add_log(
            TrainingLogModel(
                organization_id=org_id, job_id=job.id, event="TrainingQueued", message="job queued"
            )
        )
        return job

    def _detect_problem_and_target(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> tuple[str, str]:
        profile = self.profiling.get_latest_profile(org_id, dataset_id)
        if profile is None:
            raise ForbiddenError("profiling metadata is required before training")
        target = profile.target_column or ""
        if not target:
            raise ForbiddenError("target column is missing in profiling metadata")
        raw_problem = profile.problem_type
        if raw_problem == "regression":
            return ProblemType.REGRESSION.value, target
        if raw_problem in {"binary_classification", "multiclass_classification"}:
            return raw_problem, target
        raise ForbiddenError(f"unsupported problem type for phase 7: {raw_problem}")

    def run_job(self, job_id: uuid.UUID) -> TrainedModelModel:
        job = self.repo.get_job_any(job_id)
        if job is None:
            raise NotFoundError("training job not found")
        job.status = JobStatus.RUNNING.value
        job.started_at = utcnow()
        job.progress = 5
        self.repo.session.flush()
        self.repo.add_log(
            TrainingLogModel(
                organization_id=job.organization_id,
                job_id=job.id,
                event="TrainingStarted",
                message="training started",
            )
        )

        try:
            feature_set = self.features.get_feature_set(job.organization_id, job.feature_set_id)
            if feature_set is None or not feature_set.matrix_storage_key:
                raise NotFoundError("feature set matrix not found")
            dataset = self.catalog.get_dataset(job.organization_id, job.dataset_id)
            if dataset is None:
                raise NotFoundError("dataset not found")
            problem_type, target_column = self._detect_problem_and_target(
                job.organization_id, job.dataset_id
            )
            target_column = str(job.config_json.get("target_column") or target_column)

            raw = self.storage.download(self.bucket, feature_set.matrix_storage_key)
            job.progress = 20
            df = pd.read_csv(io.BytesIO(raw))
            job.progress = 35

            config = dict(job.config_json)
            config.setdefault("algorithm", "")
            outcome = run_training(
                df,
                target_column=target_column,
                problem_type_value=problem_type,
                config=config,
            )
            job.progress = 70

            model = TrainedModelModel(
                organization_id=job.organization_id,
                job_id=job.id,
                name=f"model_{dataset.name}_{job.id.hex[:8]}",
                problem_type=problem_type,
                algorithm=outcome.report["algorithm"],
                target_column=target_column,
                status=ModelStatus.DRAFT.value,
                summary=f"Validation metrics generated for {outcome.report['algorithm']}",
                feature_count=int(outcome.report["feature_schema"]["feature_count"]),
                model_size_bytes=len(outcome.model_bytes),
                training_seconds=outcome.training_seconds,
                warnings_json=outcome.warnings,
                report_json=outcome.report,
            )
            self.repo.add_trained_model(model)
            self.repo.add_version(
                ModelVersionModel(
                    organization_id=job.organization_id,
                    trained_model_id=model.id,
                    version=1,
                    immutable=True,
                )
            )

            for metric_name, value in outcome.metrics.items():
                if isinstance(value, (int, float)):
                    self.repo.add_metric(
                        TrainingMetricModel(
                            organization_id=job.organization_id,
                            trained_model_id=model.id,
                            metric_name=metric_name,
                            metric_value=float(value),
                            metric_json=None,
                        )
                    )
                else:
                    self.repo.add_metric(
                        TrainingMetricModel(
                            organization_id=job.organization_id,
                            trained_model_id=model.id,
                            metric_name=metric_name,
                            metric_value=0.0,
                            metric_json={"value": value},
                        )
                    )

            artifact_prefix = (
                f"{job.organization_id}/{dataset.project_id}/{job.dataset_id}/training/{job.id}"
            )
            artifacts: list[tuple[str, str, bytes, str]] = [
                ("model.pkl", "application/octet-stream", outcome.model_bytes, "model"),
                ("model.onnx", "application/octet-stream", b"{}", "onnx_placeholder"),
                (
                    "training_report.json",
                    "application/json",
                    json.dumps(outcome.report).encode("utf-8"),
                    "report",
                ),
                (
                    "metrics.json",
                    "application/json",
                    json.dumps(outcome.metrics).encode("utf-8"),
                    "metrics",
                ),
                (
                    "pipeline.json",
                    "application/json",
                    json.dumps(feature_set.pipeline_json).encode("utf-8"),
                    "pipeline",
                ),
                (
                    "training_config.json",
                    "application/json",
                    json.dumps(config).encode("utf-8"),
                    "training_config",
                ),
                (
                    "feature_schema.json",
                    "application/json",
                    json.dumps(outcome.report["feature_schema"]).encode("utf-8"),
                    "feature_schema",
                ),
            ]
            for filename, content_type, payload, kind in artifacts:
                key = f"{artifact_prefix}/{filename}"
                self.storage.upload(self.bucket, key, payload, content_type=content_type)
                self.repo.add_artifact(
                    TrainingArtifactModel(
                        organization_id=job.organization_id,
                        trained_model_id=model.id,
                        artifact_type=kind,
                        storage_key=key,
                        content_type=content_type,
                        size_bytes=len(payload),
                    )
                )

            self.repo.add_lineage(
                TrainingLineageModel(
                    organization_id=job.organization_id,
                    trained_model_id=model.id,
                    dataset_id=job.dataset_id,
                    dataset_version=job.dataset_version,
                    feature_set_id=job.feature_set_id,
                    random_seed=int(config.get("random_seed", 42)),
                    detail_json={
                        "algorithm": outcome.report["algorithm"],
                        "feature_version": feature_set.output_dataset_version,
                        "git_commit": str(config.get("git_commit") or ""),
                        "feature_matrix_checksum": hashlib.sha256(raw).hexdigest(),
                    },
                    git_commit=str(config.get("git_commit") or None),
                )
            )

            job.status = JobStatus.AWAITING_APPROVAL.value
            job.progress = 100
            job.completed_at = utcnow()
            self.repo.add_log(
                TrainingLogModel(
                    organization_id=job.organization_id,
                    job_id=job.id,
                    event="TrainingCompleted",
                    message="training completed and awaiting approval",
                    extra_json={"model_id": str(model.id)},
                )
            )
            return model
        except Exception as exc:
            self.repo.session.rollback()
            row = self.repo.get_job_any(job_id)
            if row is None:
                raise
            row.status = JobStatus.FAILED.value
            row.error_message = str(exc)[:2000]
            row.completed_at = utcnow()
            self.repo.add_log(
                TrainingLogModel(
                    organization_id=row.organization_id,
                    job_id=row.id,
                    level="ERROR",
                    event="TrainingFailed",
                    message=str(exc)[:1000],
                )
            )
            self.repo.session.commit()
            raise

    def approve(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID, note: str
    ) -> TrainedModelModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("training job not found")
        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError("job is not awaiting approval")
        model = self.repo.get_model_by_job(org_id, job_id)
        if model is None:
            raise NotFoundError("trained model not found")
        version = self.repo.session.scalar(
            select(ModelVersionModel).where(ModelVersionModel.trained_model_id == model.id)
        )
        if version is not None:
            version.approved = True
            version.approval_user_id = user_id
            version.approval_note = note[:1000] if note else None
        model.status = ModelStatus.APPROVED.value
        job.status = JobStatus.COMPLETED.value
        self.repo.add_log(
            TrainingLogModel(
                organization_id=org_id, job_id=job.id, event="ModelApproved", message=note[:1000]
            )
        )
        self.repo.session.commit()
        return model

    def reject(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID, reason: str
    ) -> TrainingJobModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("training job not found")
        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError("job is not awaiting approval")
        model = self.repo.get_model_by_job(org_id, job_id)
        if model:
            model.status = ModelStatus.REJECTED.value
        job.status = JobStatus.REJECTED.value
        job.error_message = reason[:2000] if reason else None
        self.repo.add_log(
            TrainingLogModel(
                organization_id=org_id, job_id=job.id, event="ModelRejected", message=reason[:1000]
            )
        )
        self.repo.session.commit()
        return job

    def list_jobs(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[TrainingJobModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_jobs(org_id)

    def get_job(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID
    ) -> TrainingJobModel | None:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_job(org_id, job_id)

    def list_models(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[TrainedModelModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_models(org_id)

    def get_model(
        self, user_id: uuid.UUID, org_id: uuid.UUID, model_id: uuid.UUID
    ) -> TrainedModelModel | None:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_model(org_id, model_id)

    def get_report(
        self, user_id: uuid.UUID, org_id: uuid.UUID, model_id: uuid.UUID
    ) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        model = self.repo.get_model(org_id, model_id)
        if model is None:
            raise NotFoundError("model not found")
        return {
            "model": model.report_json,
            "metrics": [
                {"name": m.metric_name, "value": m.metric_value, "json": m.metric_json}
                for m in self.repo.list_metrics(org_id, model_id)
            ],
            "artifacts": [
                {
                    "type": a.artifact_type,
                    "storage_key": a.storage_key,
                    "size_bytes": a.size_bytes,
                }
                for a in self.repo.list_artifacts(org_id, model_id)
            ],
        }

    def export(self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        model = self.repo.get_model_by_job(org_id, job_id)
        if model is None:
            raise NotFoundError("model not found")
        artifacts = self.repo.list_artifacts(org_id, model.id)
        out: dict[str, Any] = {"job_id": str(job_id), "model_id": str(model.id)}
        for item in artifacts:
            out[item.artifact_type] = self.storage.presigned_url(
                self.bucket, item.storage_key, expires=timedelta(hours=1)
            )
        return out

    def search(
        self, user_id: uuid.UUID, org_id: uuid.UUID, query: str, limit: int
    ) -> list[TrainedModelModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        q = f"%{query}%"
        return list(
            self.repo.session.scalars(
                select(TrainedModelModel)
                .where(
                    TrainedModelModel.organization_id == org_id,
                    TrainedModelModel.name.ilike(q) | TrainedModelModel.summary.ilike(q),
                )
                .order_by(TrainedModelModel.created_at.desc())
                .limit(limit)
            )
        )

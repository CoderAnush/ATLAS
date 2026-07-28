"""HPO application service with async execution and HITL approval."""

from __future__ import annotations

import io
import json
import uuid
from datetime import timedelta
from typing import Any

import pandas as pd
from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_feature_store.infrastructure.repository import FeatureStoreRepository
from atlas_hpo.domain import (
    MAXIMIZE_OBJECTIVES,
    MetricObjective,
    OptimizationJobStatus,
    StudyStatus,
)
from atlas_hpo.infrastructure.engine import run_optimization, trials_csv
from atlas_hpo.infrastructure.models import (
    BestTrialModel,
    OptimizationArtifactModel,
    OptimizationConfigModel,
    OptimizationJobModel,
    OptimizationLogModel,
    OptimizationMetricModel,
    OptimizationStudyModel,
    OptimizationTagModel,
    OptimizationTrialModel,
    SearchSpaceModel,
)
from atlas_hpo.infrastructure.repository import HpoRepository, utcnow
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_modeling.domain import JobStatus as TrainingJobStatus
from atlas_modeling.domain import ModelStatus, ProblemType
from atlas_modeling.infrastructure.models import TrainingJobModel
from atlas_modeling.infrastructure.repository import ModelingRepository
from atlas_profiling.infrastructure.repository import ProfilingRepository
from atlas_storage.ports import ObjectStorage
from sqlalchemy import select


class HpoService:
    def __init__(
        self,
        repo: HpoRepository,
        modeling: ModelingRepository,
        catalog: CatalogRepository,
        features: FeatureStoreRepository,
        identity: IdentityRepository,
        profiling: ProfilingRepository,
        storage: ObjectStorage,
        *,
        bucket: str,
    ) -> None:
        self.repo = repo
        self.modeling = modeling
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

    def _approved_training_job(self, org_id: uuid.UUID, training_job_id: uuid.UUID) -> TrainingJobModel:
        job = self.modeling.get_job(org_id, training_job_id)
        if job is None:
            raise NotFoundError("training job not found")
        if job.status != TrainingJobStatus.COMPLETED.value:
            raise ForbiddenError("only approved training jobs may be optimized")
        model = self.modeling.get_model_by_job(org_id, training_job_id)
        if model is None or model.status != ModelStatus.APPROVED.value:
            raise ForbiddenError("training job must have an approved trained model")
        return job

    def _detect_problem_and_target(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> tuple[str, str]:
        profile = self.profiling.get_latest_profile(org_id, dataset_id)
        if profile is None:
            raise ForbiddenError("profiling metadata is required before optimization")
        target = profile.target_column or ""
        if not target:
            raise ForbiddenError("target column is missing in profiling metadata")
        raw_problem = profile.problem_type
        if raw_problem == ProblemType.REGRESSION.value:
            return ProblemType.REGRESSION.value, target
        if raw_problem in {
            ProblemType.BINARY_CLASSIFICATION.value,
            ProblemType.MULTICLASS_CLASSIFICATION.value,
        }:
            return raw_problem, target
        raise ForbiddenError(f"unsupported problem type for phase 8: {raw_problem}")

    def enqueue(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        training_job_id: uuid.UUID,
        body: dict[str, Any],
    ) -> OptimizationJobModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        training_job = self._approved_training_job(org_id, training_job_id)
        model = self.modeling.get_model_by_job(org_id, training_job_id)
        assert model is not None
        optimizer = str(body.get("optimizer") or "optuna")
        metric_objective = str(body.get("metric_objective") or "accuracy")
        budget = dict(body.get("budget") or {})
        config = dict(body.get("config") or {})
        direction = (
            "maximize"
            if MetricObjective(metric_objective) in MAXIMIZE_OBJECTIVES
            else "minimize"
        )
        job = OptimizationJobModel(
            organization_id=org_id,
            training_job_id=training_job_id,
            feature_set_id=training_job.feature_set_id,
            dataset_id=training_job.dataset_id,
            optimizer=optimizer,
            metric_objective=metric_objective,
            direction=direction,
            status=OptimizationJobStatus.QUEUED.value,
            progress=0,
            budget_json=budget,
            config_json=config,
            created_by_user_id=user_id,
            remaining_trials=int(budget.get("max_trials", 10)),
        )
        self.repo.add_job(job)
        self.repo.add_config(
            OptimizationConfigModel(
                organization_id=org_id,
                job_id=job.id,
                config_json={"optimizer": optimizer, "metric_objective": metric_objective, **body},
            )
        )
        self.repo.add_log(
            OptimizationLogModel(
                organization_id=org_id,
                job_id=job.id,
                event="OptimizationQueued",
                message="optimization job queued",
                extra_json={"training_job_id": str(training_job_id), "algorithm": model.algorithm},
            )
        )
        return job

    def run_job(self, job_id: uuid.UUID) -> OptimizationStudyModel:
        job = self.repo.get_job_any(job_id)
        if job is None:
            raise NotFoundError("optimization job not found")
        job.status = OptimizationJobStatus.RUNNING.value
        job.started_at = utcnow()
        job.progress = 5
        self.repo.add_log(
            OptimizationLogModel(
                organization_id=job.organization_id,
                job_id=job.id,
                event="OptimizationStarted",
                message="optimization started",
            )
        )

        try:
            training_job = self._approved_training_job(job.organization_id, job.training_job_id)
            base_model = self.modeling.get_model_by_job(job.organization_id, job.training_job_id)
            if base_model is None:
                raise NotFoundError("trained model not found")
            feature_set = self.features.get_feature_set(job.organization_id, training_job.feature_set_id)
            if feature_set is None or not feature_set.matrix_storage_key:
                raise NotFoundError("feature set matrix not found")
            dataset = self.catalog.get_dataset(job.organization_id, training_job.dataset_id)
            if dataset is None:
                raise NotFoundError("dataset not found")

            problem_type, target_column = self._detect_problem_and_target(
                job.organization_id, training_job.dataset_id
            )
            raw = self.storage.download(self.bucket, feature_set.matrix_storage_key)
            job.progress = 20
            df = pd.read_csv(io.BytesIO(raw))
            job.progress = 35

            algorithm = str(job.config_json.get("algorithm") or base_model.algorithm)
            base_config = dict(training_job.config_json or {})
            base_config.update(job.config_json)
            base_config["algorithm"] = algorithm

            study = OptimizationStudyModel(
                organization_id=job.organization_id,
                job_id=job.id,
                study_name=f"study_{job.id.hex[:8]}",
                optimizer=job.optimizer,
                direction=job.direction,
                status=StudyStatus.RUNNING.value,
                problem_type=problem_type,
                algorithm=algorithm,
                metric_objective=job.metric_objective,
                feature_count=0,
            )
            self.repo.add_study(study)

            result = run_optimization(
                df,
                target_column=str(base_config.get("target_column") or target_column),
                problem_type=problem_type,
                algorithm=algorithm,
                optimizer=job.optimizer,
                metric_objective=job.metric_objective,
                budget=job.budget_json,
                base_config=base_config,
            )
            job.progress = 70

            history = [
                {
                    "trial_number": trial.trial_number,
                    "status": trial.status,
                    "objective_value": trial.objective_value,
                    "params": trial.params,
                    "metrics": trial.metrics,
                    "duration_seconds": trial.training_seconds,
                }
                for trial in result.trials
            ]
            study.study_name = result.study_name
            study.status = StudyStatus.COMPLETED.value
            study.direction = result.direction
            study.optimizer = result.optimizer
            study.feature_count = int(result.best_report.get("feature_schema", {}).get("feature_count", 0))
            study.total_trials = len(result.trials)
            study.completed_trials = len([t for t in result.trials if t.status == "completed"])
            study.pruned_trials = len([t for t in result.trials if t.status == "pruned"])
            study.best_trial_number = min(
                (t.trial_number for t in result.trials if t.objective_value == result.best_value),
                default=None,
            )
            study.best_score = result.best_value
            study.best_params_json = result.best_params
            study.report_json = {
                "problem_type": problem_type,
                "algorithm": algorithm,
                "metric_objective": job.metric_objective,
                "best_trial": {
                    "score": result.best_value,
                    "params": result.best_params,
                    "metrics": result.best_metrics,
                    "report": result.best_report,
                },
                "summary": result.summary,
            }
            study.history_json = {"trials": history, **result.summary.get("visualizations", {})}
            study.started_at = job.started_at
            study.completed_at = utcnow()

            search_space_row = SearchSpaceModel(
                organization_id=job.organization_id,
                study_id=study.id,
                algorithm=algorithm,
                search_space_json=result.search_space,
            )
            self.repo.add_search_space(search_space_row)
            self.repo.add_tag(
                OptimizationTagModel(
                    organization_id=job.organization_id,
                    study_id=study.id,
                    tag_key="parallel_execution",
                    tag_value=result.summary["parallel_execution"]["mode"],
                )
            )

            best_trial_id: uuid.UUID | None = None
            for trial in result.trials:
                trial_row = OptimizationTrialModel(
                    organization_id=job.organization_id,
                    study_id=study.id,
                    trial_number=trial.trial_number,
                    status=trial.status,
                    objective_value=trial.objective_value,
                    params_json=trial.params,
                    metrics_json=trial.metrics,
                    user_attrs_json={"report": trial.report},
                    duration_seconds=trial.training_seconds,
                    started_at=job.started_at,
                    completed_at=utcnow(),
                )
                self.repo.add_trial(trial_row)
                if trial.objective_value == result.best_value and trial.status == "completed":
                    best_trial_id = trial_row.id

            if best_trial_id is not None and result.best_value is not None:
                self.repo.add_best_trial(
                    BestTrialModel(
                        organization_id=job.organization_id,
                        study_id=study.id,
                        trial_id=best_trial_id,
                        score=float(result.best_value),
                        params_json=result.best_params,
                        metrics_json=result.best_metrics,
                        report_json=result.best_report,
                    )
                )

            for metric_name, value in result.best_metrics.items():
                if isinstance(value, (int, float)):
                    self.repo.add_metric(
                        OptimizationMetricModel(
                            organization_id=job.organization_id,
                            study_id=study.id,
                            metric_name=metric_name,
                            metric_value=float(value),
                            metric_json=None,
                        )
                    )
                else:
                    self.repo.add_metric(
                        OptimizationMetricModel(
                            organization_id=job.organization_id,
                            study_id=study.id,
                            metric_name=metric_name,
                            metric_value=0.0,
                            metric_json={"value": value},
                        )
                    )

            artifact_prefix = f"{job.organization_id}/{dataset.project_id}/{dataset.id}/hpo/{job.id}"
            artifact_payloads: list[tuple[str, str, bytes, str]] = [
                (
                    "study.json",
                    "application/json",
                    json.dumps(study.report_json).encode("utf-8"),
                    "study",
                ),
                (
                    "best_params.json",
                    "application/json",
                    json.dumps(result.best_params).encode("utf-8"),
                    "best_params",
                ),
                ("trials.csv", "text/csv", trials_csv(result.trials), "trials"),
                (
                    "optimization_report.json",
                    "application/json",
                    json.dumps(study.report_json).encode("utf-8"),
                    "optimization_report",
                ),
                (
                    "training_metrics.json",
                    "application/json",
                    json.dumps(result.best_metrics).encode("utf-8"),
                    "training_metrics",
                ),
                (
                    "optimization_config.json",
                    "application/json",
                    json.dumps(
                        {
                            "optimizer": job.optimizer,
                            "metric_objective": job.metric_objective,
                            "budget": job.budget_json,
                            "config": job.config_json,
                        }
                    ).encode("utf-8"),
                    "optimization_config",
                ),
                (
                    "optimization_history.json",
                    "application/json",
                    json.dumps(study.history_json).encode("utf-8"),
                    "optimization_history",
                ),
                (
                    "plots.json",
                    "application/json",
                    json.dumps(result.summary["visualizations"]).encode("utf-8"),
                    "plots_placeholder",
                ),
            ]
            for filename, content_type, payload, artifact_type in artifact_payloads:
                key = f"{artifact_prefix}/{filename}"
                self.storage.upload(self.bucket, key, payload, content_type=content_type)
                self.repo.add_artifact(
                    OptimizationArtifactModel(
                        organization_id=job.organization_id,
                        study_id=study.id,
                        artifact_type=artifact_type,
                        storage_key=key,
                        content_type=content_type,
                        size_bytes=len(payload),
                    )
                )

            job.status = OptimizationJobStatus.AWAITING_APPROVAL.value
            job.progress = 100
            job.best_score = result.best_value
            job.trials_completed = study.completed_trials
            job.remaining_trials = max(0, study.total_trials - study.completed_trials)
            job.completed_at = utcnow()
            self.repo.add_log(
                OptimizationLogModel(
                    organization_id=job.organization_id,
                    job_id=job.id,
                    event="OptimizationCompleted",
                    message="optimization completed and awaiting approval",
                    extra_json={"study_id": str(study.id), "best_score": result.best_value},
                )
            )
            return study
        except Exception as exc:
            self.repo.session.rollback()
            row = self.repo.get_job_any(job_id)
            if row is None:
                raise
            row.status = OptimizationJobStatus.FAILED.value
            row.error_message = str(exc)[:2000]
            row.completed_at = utcnow()
            self.repo.add_log(
                OptimizationLogModel(
                    organization_id=row.organization_id,
                    job_id=row.id,
                    level="ERROR",
                    event="OptimizationFailed",
                    message=str(exc)[:1000],
                )
            )
            self.repo.session.commit()
            raise

    def list_jobs(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[OptimizationJobModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_jobs(org_id)

    def get_job(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID
    ) -> OptimizationJobModel | None:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_job(org_id, job_id)

    def list_studies(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[OptimizationStudyModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_studies(org_id)

    def get_study(
        self, user_id: uuid.UUID, org_id: uuid.UUID, study_id: uuid.UUID
    ) -> OptimizationStudyModel | None:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_study(org_id, study_id)

    def get_report(
        self, user_id: uuid.UUID, org_id: uuid.UUID, study_id: uuid.UUID
    ) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        study = self.repo.get_study(org_id, study_id)
        if study is None:
            raise NotFoundError("study not found")
        search_space = self.repo.get_search_space(study.id)
        return {
            "study": study.report_json,
            "history": study.history_json,
            "search_space": search_space.search_space_json if search_space else {},
            "trials": [
                {
                    "trial_number": t.trial_number,
                    "status": t.status,
                    "objective_value": t.objective_value,
                    "params": t.params_json,
                    "metrics": t.metrics_json,
                    "duration_seconds": t.duration_seconds,
                }
                for t in self.repo.list_trials(org_id, study.id)
            ],
            "artifacts": [
                {
                    "type": a.artifact_type,
                    "storage_key": a.storage_key,
                    "size_bytes": a.size_bytes,
                }
                for a in self.repo.list_artifacts(org_id, study.id)
            ],
        }

    def approve(
        self, user_id: uuid.UUID, org_id: uuid.UUID, study_id: uuid.UUID, note: str
    ) -> OptimizationStudyModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        study = self.repo.get_study(org_id, study_id)
        if study is None:
            raise NotFoundError("study not found")
        if study.status != StudyStatus.COMPLETED.value:
            raise ForbiddenError("study is not awaiting approval")
        study.status = StudyStatus.APPROVED.value
        study.approved_by_user_id = user_id
        study.approval_note = note[:1000] if note else None
        job = self.repo.get_job(org_id, study.job_id)
        if job is not None:
            job.status = OptimizationJobStatus.COMPLETED.value
        self.repo.add_log(
            OptimizationLogModel(
                organization_id=org_id,
                job_id=study.job_id,
                event="OptimizationApproved",
                message=note[:1000] if note else "approved",
            )
        )
        self.repo.session.commit()
        return study

    def reject(
        self, user_id: uuid.UUID, org_id: uuid.UUID, study_id: uuid.UUID, reason: str
    ) -> OptimizationStudyModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        study = self.repo.get_study(org_id, study_id)
        if study is None:
            raise NotFoundError("study not found")
        if study.status != StudyStatus.COMPLETED.value:
            raise ForbiddenError("study is not awaiting approval")
        study.status = StudyStatus.REJECTED.value
        study.approval_note = reason[:1000] if reason else None
        job = self.repo.get_job(org_id, study.job_id)
        if job is not None:
            job.status = OptimizationJobStatus.REJECTED.value
            job.error_message = reason[:2000] if reason else None
        self.repo.add_log(
            OptimizationLogModel(
                organization_id=org_id,
                job_id=study.job_id,
                event="OptimizationRejected",
                message=reason[:1000] if reason else "rejected",
            )
        )
        self.repo.session.commit()
        return study

    def export(self, user_id: uuid.UUID, org_id: uuid.UUID, study_id: uuid.UUID) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        study = self.repo.get_study(org_id, study_id)
        if study is None:
            raise NotFoundError("study not found")
        artifacts = self.repo.list_artifacts(org_id, study.id)
        out: dict[str, Any] = {"study_id": str(study_id), "job_id": str(study.job_id)}
        for item in artifacts:
            out[item.artifact_type] = self.storage.presigned_url(
                self.bucket, item.storage_key, expires=timedelta(hours=1)
            )
        return out

    def search(
        self, user_id: uuid.UUID, org_id: uuid.UUID, query: str, limit: int
    ) -> list[OptimizationStudyModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        q = f"%{query}%"
        return list(
            self.repo.session.scalars(
                select(OptimizationStudyModel)
                .where(
                    OptimizationStudyModel.organization_id == org_id,
                    OptimizationStudyModel.study_name.ilike(q)
                    | OptimizationStudyModel.algorithm.ilike(q)
                    | OptimizationStudyModel.metric_objective.ilike(q),
                )
                .order_by(OptimizationStudyModel.created_at.desc())
                .limit(limit)
            )
        )

"""Feature store application service with HITL approval flow."""

from __future__ import annotations

import hashlib
import io
import logging
import uuid
from datetime import timedelta
from typing import Any

from atlas_catalog.domain import DatasetStatus
from atlas_catalog.infrastructure.models import (
    DatasetLineageModel,
    DatasetStatisticsModel,
    DatasetStorageModel,
    DatasetVersionModel,
)
from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_core.ids import uuid7
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_profiling.infrastructure.loader import load_dataframe
from atlas_profiling.infrastructure.repository import ProfilingRepository
from atlas_storage.ports import ObjectStorage
from prometheus_client import Counter, Histogram

from atlas_feature_store.domain import FeatureSetStatus, JobStatus
from atlas_feature_store.infrastructure.engine import (
    apply_pipeline,
    estimate_usefulness,
    json_safe,
    memory_safe_sample,
    run_feature_engineering,
)
from atlas_feature_store.infrastructure.models import (
    FeatureJobModel,
    FeatureLineageModel,
    FeatureRegistryModel,
    FeatureSetModel,
    FeatureStatisticsModel,
    FeatureTransformationModel,
    FeatureVersionModel,
    FeatureViewModel,
)
from atlas_feature_store.infrastructure.repository import (
    FeatureStoreRepository,
    utcnow,
)

logger = logging.getLogger("atlas.features")

FEATURE_GENERATION_STARTED = Counter(
    "atlas_features_generation_started_total", "Feature generation jobs started"
)
FEATURE_GENERATION_COMPLETED = Counter(
    "atlas_features_generation_completed_total", "Feature generation jobs completed"
)
FEATURE_GENERATION_FAILED = Counter(
    "atlas_features_generation_failed_total", "Feature generation jobs failed"
)
FEATURE_CREATED = Counter("atlas_features_created_total", "Features created")
FEATURE_PIPELINE_CREATED = Counter(
    "atlas_features_pipeline_created_total", "Feature pipelines created"
)
FEATURE_STORED = Counter("atlas_features_stored_total", "Features stored")
APPROVAL_GRANTED = Counter("atlas_features_approval_granted_total", "Approvals granted")
APPROVAL_REJECTED = Counter("atlas_features_approval_rejected_total", "Approvals rejected")
FEATURE_ENGINEERING_DURATION = Histogram(
    "atlas_features_engineering_duration_seconds",
    "Feature engineering duration",
    buckets=(1, 5, 15, 60, 180, 600),
)


class FeatureStoreService:
    """Human-in-the-loop feature engineering service.

    Flow:
    1. enqueue() creates a queued job
    2. run_job() analyzes data, generates feature pipeline, sets status to awaiting_approval
    3. approve() applies pipeline to data, creates new dataset version
    4. reject() marks job as rejected
    """

    def __init__(
        self,
        repo: FeatureStoreRepository,
        catalog: CatalogRepository,
        identity: IdentityRepository,
        profiling: ProfilingRepository,
        storage: ObjectStorage,
        *,
        bucket: str,
    ) -> None:
        self.repo = repo
        self.catalog = catalog
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
        dataset_id: uuid.UUID,
        config: dict[str, Any] | None = None,
    ) -> FeatureJobModel:
        """Queue a new feature engineering job for analysis."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        dataset = self.catalog.get_dataset(org_id, dataset_id)
        if dataset is None or dataset.status == DatasetStatus.DELETED.value:
            raise NotFoundError("dataset not found")
        if dataset.status != DatasetStatus.READY.value:
            raise ForbiddenError("dataset is not ready for feature engineering")

        job = FeatureJobModel(
            organization_id=org_id,
            dataset_id=dataset_id,
            dataset_version=dataset.current_version,
            status=JobStatus.QUEUED.value,
            progress=0,
            config=config or {},
            created_by_user_id=user_id,
        )
        self.repo.add_job(job)
        self.repo.session.flush()

        self.repo.append_history(job, "JobCreated", {"dataset_id": str(dataset_id)})

        logger.info(
            "JobCreated",
            extra={
                "tenant_id": str(org_id),
                "dataset_id": str(dataset_id),
                "job_id": str(job.id),
            },
        )
        return job

    def run_job(self, job_id: uuid.UUID) -> FeatureSetModel:
        """Execute feature engineering analysis (worker entrypoint).

        Generates a feature engineering pipeline and feature set, sets status to AWAITING_APPROVAL.
        Does NOT create a new dataset version - that happens on approve().
        """
        import time

        started = time.perf_counter()

        job = self.repo.get_job_any(job_id)
        if job is None:
            raise NotFoundError("feature job not found")

        org_id = job.organization_id
        dataset_id = job.dataset_id

        job.status = JobStatus.RUNNING.value
        job.started_at = utcnow()
        job.progress = 5
        self.repo.session.flush()
        FEATURE_GENERATION_STARTED.inc()

        self.repo.append_history(job, "FeatureGenerationStarted")
        logger.info(
            "FeatureGenerationStarted",
            extra={
                "tenant_id": str(org_id),
                "dataset_id": str(dataset_id),
                "job_id": str(job_id),
            },
        )

        try:
            dataset = self.catalog.get_dataset(org_id, dataset_id)
            if dataset is None:
                raise NotFoundError("dataset not found")

            version = self.catalog.get_version(org_id, dataset_id, job.dataset_version)
            if version is None:
                raise NotFoundError("dataset version not found")

            job.progress = 15
            raw = self.storage.download(self.bucket, version.storage_key)

            job.progress = 30
            df = load_dataframe(raw, version.original_filename)

            job.progress = 40

            profile_row = self.profiling.get_latest_profile(org_id, dataset_id)
            profile = profile_row.profile_json if profile_row else None

            job.progress = 50

            # Sample if huge
            if len(df) > 200000:
                df = memory_safe_sample(df, max_rows=200000)

            config = dict(job.config or {})
            if not config.get("target") and profile_row and profile_row.target_column:
                config["target"] = profile_row.target_column
            job.config = config

            result = run_feature_engineering(df, profile, config=config)

            job.progress = 70
            FEATURE_PIPELINE_CREATED.inc()

            summary_obj = result.get("summary") or {}
            if isinstance(summary_obj, dict):
                summary_text = (
                    f"Features {summary_obj.get('output_shape', result.get('matrix_shape'))}; "
                    f"usefulness {summary_obj.get('usefulness_score', 0)}"
                )
                quality = float(summary_obj.get("usefulness_score") or 0.0)
            else:
                summary_text = str(summary_obj)
                quality = float(estimate_usefulness(result.get("report") or {}))

            drop_candidates = (result.get("report") or {}).get("validation", {}).get(
                "drop_candidates"
            ) or {}
            if isinstance(drop_candidates, dict):
                rejected_list = list(drop_candidates.get("constant") or [])
            else:
                rejected_list = list(drop_candidates)

            shape = result.get("matrix_shape") or (0, 0)
            rows = int(shape[0]) if not isinstance(shape, int) else 0
            cols = int(shape[1]) if not isinstance(shape, int) else int(shape)

            # Create feature set
            feature_set = FeatureSetModel(
                organization_id=org_id,
                job_id=job.id,
                dataset_id=dataset_id,
                name=f"feature_set_{dataset.name}_{job.id.hex[:8]}",
                status=FeatureSetStatus.DRAFT.value,
                summary=summary_text,
                selected_features=result.get("preview_columns", [])[:50],
                rejected_features=rejected_list,
                pipeline_json=json_safe(result["pipeline"]),
                report_json=json_safe(result["report"]),
                graph_json=json_safe(result.get("visualizations") or result.get("graph") or {}),
                recommendations_json=json_safe(
                    {"recommendations": result.get("recommendations", [])}
                ),
                rows=rows,
                columns=cols,
                quality_score=quality,
            )
            self.repo.add_feature_set(feature_set)

            # Add transformations
            steps = result["pipeline"].get("steps", [])
            for step_idx, step_data in enumerate(steps):
                kind_raw = step_data.get("kind", "unknown")
                step = FeatureTransformationModel(
                    organization_id=org_id,
                    feature_set_id=feature_set.id,
                    step_order=step_idx,
                    kind=str(getattr(kind_raw, "value", kind_raw)),
                    params=json_safe(step_data.get("params", {}) or {}),
                    input_columns=list(
                        step_data.get("columns") or step_data.get("input_columns") or []
                    ),
                    output_columns=list(step_data.get("output_columns") or []),
                    reason=str(
                        (step_data.get("params") or {}).get("reason")
                        or step_data.get("reason")
                        or ""
                    ),
                    approved=bool(step_data.get("approved", True)),
                )
                self.repo.add_transformation(step)

            job.progress = 80

            # Add registry features for top features
            feature_scores = result["report"].get("feature_scores", {})
            top_features = sorted(
                feature_scores.items(),
                key=lambda x: x[1].get("overall_score", 0),
                reverse=True,
            )[:20]

            for feat_name, feat_stats in top_features:
                registry_feature = FeatureRegistryModel(
                    organization_id=org_id,
                    name=feat_name,
                    feature_set_id=feature_set.id,
                    kind="numeric",
                    dtype="float64",
                    description=f"Generated feature from {feat_name}",
                    usefulness_score=feat_stats.get("overall_score", 0.0),
                    selected=True,
                    owner_user_id=job.created_by_user_id,
                )
                self.repo.add_registry_feature(registry_feature)

                # Add statistics
                stats = FeatureStatisticsModel(
                    organization_id=org_id,
                    feature_id=registry_feature.id,
                    stats_json=json_safe(feat_stats),
                    uniqueness=feat_stats.get("uniqueness", 0.0),
                    variance=feat_stats.get("variance", 0.0),
                    missing_pct=feat_stats.get("missing_pct", 0.0),
                    correlation=feat_stats.get("correlation", 0.0),
                    redundancy=feat_stats.get("redundancy", 0.0),
                    overall_score=feat_stats.get("overall_score", 0.0),
                )
                self.repo.add_statistics(stats)

                FEATURE_CREATED.inc()

            # Add lineage
            lineage = FeatureLineageModel(
                organization_id=org_id,
                feature_set_id=feature_set.id,
                parent_type="dataset",
                parent_id=str(dataset_id),
                relation="derived_from",
                detail_json={
                    "job_id": str(job.id),
                    "dataset_version": job.dataset_version,
                    "feature_count": len(top_features),
                },
            )
            self.repo.add_lineage(lineage)

            self.repo.append_history(
                job,
                "FeaturePipelineCreated",
                {
                    "step_count": len(steps),
                    "feature_count": len(top_features),
                    "quality_score": feature_set.quality_score,
                },
            )

            job.progress = 90

            job.status = JobStatus.AWAITING_APPROVAL.value
            job.progress = 100
            job.completed_at = utcnow()

            FEATURE_ENGINEERING_DURATION.observe(time.perf_counter() - started)

            logger.info(
                "FeatureGenerationCompleted",
                extra={
                    "tenant_id": str(org_id),
                    "dataset_id": str(dataset_id),
                    "job_id": str(job_id),
                    "feature_count": len(top_features),
                },
            )

            return feature_set

        except Exception as exc:
            self.repo.session.rollback()
            job = self.repo.get_job_any(job_id)
            if job is None:
                raise
            job.status = JobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.completed_at = utcnow()
            FEATURE_GENERATION_FAILED.inc()
            self.repo.append_history(job, "FeatureGenerationFailed", {"error": str(exc)[:500]})
            self.repo.session.commit()
            logger.exception("FeatureGenerationFailed", extra={"job_id": str(job_id)})
            raise

    def approve(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        job_id: uuid.UUID,
        edited_steps: list[dict[str, Any]] | None = None,
        selected_features: list[str] | None = None,
    ) -> FeatureSetModel:
        """Approve and apply the feature engineering pipeline.

        Creates a new dataset version with feature matrix.
        """
        self._require(user_id, org_id, Permission.PROJECT_WRITE)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("feature job not found")

        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError(f"job is not awaiting approval (status={job.status})")

        feature_set = self.repo.get_feature_set_by_job(org_id, job_id)
        if feature_set is None:
            raise NotFoundError("feature set not found for job")

        steps = (
            edited_steps if edited_steps is not None else feature_set.pipeline_json.get("steps", [])
        )

        if edited_steps is not None:
            feature_set.pipeline_json = {
                "version": feature_set.pipeline_json.get("version", "1.0.0"),
                "steps": steps,
            }
            self.repo.append_history(
                job,
                "PipelineEdited",
                {
                    "original_steps": len(feature_set.pipeline_json.get("steps", [])),
                    "new_steps": len(steps),
                },
            )

        job.status = JobStatus.APPLYING.value
        self.repo.session.flush()

        try:
            dataset = self.catalog.get_dataset(org_id, job.dataset_id)
            if dataset is None:
                raise NotFoundError("dataset not found")

            version = self.catalog.get_version(org_id, job.dataset_id, job.dataset_version)
            if version is None:
                raise NotFoundError("dataset version not found")

            raw = self.storage.download(self.bucket, version.storage_key)
            df = load_dataframe(raw, version.original_filename)

            # Sample if huge
            if len(df) > 200000:
                df = memory_safe_sample(df, max_rows=200000)

            feature_matrix, report = apply_pipeline(df, steps)

            pipeline_target = feature_set.pipeline_json.get("target")
            if (
                pipeline_target
                and pipeline_target in df.columns
                and pipeline_target not in feature_matrix.columns
            ):
                feature_matrix = feature_matrix.copy()
                feature_matrix[pipeline_target] = df[pipeline_target].to_numpy()

            # Optionally filter to selected features (always retain supervised target)
            if selected_features:
                available_features = [f for f in selected_features if f in feature_matrix.columns]
                if (
                    pipeline_target
                    and pipeline_target in feature_matrix.columns
                    and pipeline_target not in available_features
                ):
                    available_features.append(pipeline_target)
                if available_features:
                    feature_matrix = feature_matrix[available_features]

            csv_buffer = io.BytesIO()
            feature_matrix.to_csv(csv_buffer, index=False)
            csv_bytes = csv_buffer.getvalue()

            checksum = hashlib.sha256(csv_bytes).hexdigest()

            new_version_no = dataset.current_version + 1
            storage_filename = f"{uuid7()}.csv"
            storage_key = (
                f"{org_id}/{dataset.project_id}/{dataset.id}/{new_version_no}/{storage_filename}"
            )

            self.storage.upload(self.bucket, storage_key, csv_bytes, content_type="text/csv")

            new_version = DatasetVersionModel(
                id=uuid7(),
                organization_id=org_id,
                dataset_id=dataset.id,
                version=new_version_no,
                status=DatasetStatus.READY.value,
                storage_key=storage_key,
                storage_filename=storage_filename,
                original_filename=f"features_{version.original_filename}",
                extension=".csv",
                mime_type="text/csv",
                encoding="utf-8",
                size_bytes=len(csv_bytes),
                checksum_sha256=checksum,
                row_estimate=len(feature_matrix),
                column_estimate=len(feature_matrix.columns),
                uploaded_by_user_id=user_id,
            )
            self.catalog.add_version(new_version)

            storage_record = DatasetStorageModel(
                id=uuid7(),
                organization_id=org_id,
                dataset_version_id=new_version.id,
                bucket=self.bucket,
                object_key=storage_key,
                storage_class="STANDARD",
            )
            self.catalog.add_storage(storage_record)

            stats_record = DatasetStatisticsModel(
                id=uuid7(),
                organization_id=org_id,
                dataset_version_id=new_version.id,
                row_estimate=len(feature_matrix),
                column_estimate=len(feature_matrix.columns),
                size_bytes=len(csv_bytes),
                extra={
                    "featured": True,
                    "source_version": job.dataset_version,
                    "feature_set_id": str(feature_set.id),
                },
            )
            self.catalog.add_stats(stats_record)

            self.catalog.add_lineage(
                DatasetLineageModel(
                    id=uuid7(),
                    organization_id=org_id,
                    dataset_id=dataset.id,
                    parent_dataset_id=dataset.id,
                    parent_version_id=version.id,
                    relation="featured_from",
                    metadata_json={
                        "job_id": str(job_id),
                        "source_version": job.dataset_version,
                        "output_version": new_version_no,
                        "steps": len(steps),
                        "feature_set_id": str(feature_set.id),
                    },
                )
            )

            dataset.current_version = new_version_no
            dataset.status = DatasetStatus.READY.value

            # Update feature set
            feature_set.status = FeatureSetStatus.MATERIALIZED.value
            feature_set.matrix_storage_key = storage_key
            feature_set.output_dataset_version = new_version_no
            feature_set.rows = len(feature_matrix)
            feature_set.columns = len(feature_matrix.columns)

            # Create feature version (immutable)
            feature_version = FeatureVersionModel(
                organization_id=org_id,
                feature_set_id=feature_set.id,
                version=1,
                pipeline_json=feature_set.pipeline_json,
                dataset_id=job.dataset_id,
                dataset_version=new_version_no,
                immutable=True,
            )
            self.repo.add_version(feature_version)

            # Create feature view
            feature_view = FeatureViewModel(
                organization_id=org_id,
                name=f"view_{feature_set.name}",
                description=f"Feature view for {feature_set.name}",
                feature_set_id=feature_set.id,
                feature_version_id=feature_version.id,
                feature_names=list(feature_matrix.columns),
                offline_key=storage_key,
                online_enabled=False,
            )
            self.repo.add_view(feature_view)

            self.repo.append_history(job, "TransformationApplied", {"step_count": len(steps)})
            self.repo.append_history(
                job,
                "ApprovalGranted",
                {
                    "user_id": str(user_id),
                    "output_version": new_version_no,
                    "feature_count": len(feature_matrix.columns),
                },
            )

            APPROVAL_GRANTED.inc()
            FEATURE_STORED.inc(len(feature_matrix.columns))
            FEATURE_GENERATION_COMPLETED.inc()

            logger.info(
                "ApprovalGranted",
                extra={
                    "tenant_id": str(org_id),
                    "job_id": str(job_id),
                    "user_id": str(user_id),
                    "output_version": new_version_no,
                },
            )

            job.status = JobStatus.COMPLETED.value

            # Commit before response so follow-up GETs see the new version
            # (FastAPI yield-deps commit after the response is sent).
            self.repo.session.commit()
            return feature_set

        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Apply failed: {exc}"[:2000]
            FEATURE_GENERATION_FAILED.inc()
            self.repo.append_history(job, "ApplyFailed", {"error": str(exc)[:500]})
            logger.exception("ApplyFailed", extra={"job_id": str(job_id)})
            raise

    def reject(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID, reason: str = ""
    ) -> FeatureJobModel:
        """Reject a feature engineering job."""
        self._require(user_id, org_id, Permission.PROJECT_WRITE)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("feature job not found")

        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError(f"job is not awaiting approval (status={job.status})")

        feature_set = self.repo.get_feature_set_by_job(org_id, job_id)
        if feature_set:
            feature_set.status = FeatureSetStatus.REJECTED.value

        job.status = JobStatus.REJECTED.value
        job.error_message = reason[:2000] if reason else None

        self.repo.append_history(
            job, "ApprovalRejected", {"user_id": str(user_id), "reason": reason}
        )

        APPROVAL_REJECTED.inc()

        logger.info(
            "ApprovalRejected",
            extra={
                "tenant_id": str(org_id),
                "job_id": str(job_id),
                "user_id": str(user_id),
                "reason": reason,
            },
        )

        self.repo.session.commit()
        return job

    def get_summary(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> dict[str, Any]:
        """Get the latest feature engineering summary for a dataset."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        job = self.repo.latest_job_for_dataset(org_id, dataset_id)
        if job is None:
            raise NotFoundError("no feature jobs found for dataset")

        feature_set = self.repo.get_feature_set_by_job(org_id, job.id)

        result: dict[str, Any] = {
            "dataset_id": dataset_id,
            "job_id": job.id,
            "status": job.status,
            "summary": feature_set.summary if feature_set else "",
        }

        if feature_set:
            result["feature_set_id"] = feature_set.id
            result["quality_score"] = feature_set.quality_score
            result["recommendations"] = feature_set.recommendations_json.get("recommendations", [])

        return result

    def list_jobs(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[FeatureJobModel]:
        """List all feature engineering jobs for the organization."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_jobs(org_id)

    def get_job(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID
    ) -> FeatureJobModel | None:
        """Get a specific feature job."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_job(org_id, job_id)

    def list_feature_sets(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[FeatureSetModel]:
        """List feature sets for the organization."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_feature_sets(org_id)

    def get_feature_set(
        self, user_id: uuid.UUID, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> FeatureSetModel | None:
        """Get a specific feature set."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.get_feature_set(org_id, feature_set_id)

    def get_report(
        self, user_id: uuid.UUID, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> dict[str, Any]:
        """Get report details from feature set."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        feature_set = self.repo.get_feature_set(org_id, feature_set_id)
        if feature_set is None:
            raise NotFoundError("feature set not found")

        return {
            "id": feature_set.id,
            "job_id": feature_set.job_id,
            "report": feature_set.report_json,
            "graph": feature_set.graph_json,
            "recommendations": feature_set.recommendations_json,
            "created_at": feature_set.created_at.isoformat(),
        }

    def get_lineage(
        self, user_id: uuid.UUID, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get lineage for a feature set."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        lineages = self.repo.list_lineage_for_set(org_id, feature_set_id)
        return [
            {
                "id": str(lin.id),
                "parent_type": lin.parent_type,
                "parent_id": lin.parent_id,
                "relation": lin.relation,
                "detail": lin.detail_json,
                "created_at": lin.created_at.isoformat(),
            }
            for lin in lineages
        ]

    def search(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        query: str,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[FeatureSetModel]:
        """Search feature sets."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.search_feature_sets(org_id, query, tags, limit)

    def export(self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
        """Export feature matrix or pipeline.

        Returns presigned URL for the feature matrix or pipeline JSON.
        """
        self._require(user_id, org_id, Permission.PROJECT_READ)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("feature job not found")

        result: dict[str, Any] = {"job_id": job_id, "status": job.status}

        feature_set = self.repo.get_feature_set_by_job(org_id, job_id)
        if feature_set and feature_set.matrix_storage_key:
            url = self.storage.presigned_url(
                self.bucket, feature_set.matrix_storage_key, expires=timedelta(hours=1)
            )
            result["data_url"] = url
            result["expires_in_seconds"] = 3600

        if feature_set:
            result["pipeline"] = feature_set.pipeline_json

        return result

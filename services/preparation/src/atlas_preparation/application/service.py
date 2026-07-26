"""Preparation application service with HITL approval flow."""

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

from atlas_preparation.domain import JobStatus, PlanStatus
from atlas_preparation.infrastructure.engine import (
    apply_recipe,
    quality_snapshot,
    run_data_cleaning,
)
from atlas_preparation.infrastructure.models import (
    CleaningJobModel,
    CleaningPlanModel,
    CleaningRecipeModel,
    CleaningReportModel,
    CleaningStepModel,
    PreparedDatasetModel,
    QualityImprovementModel,
)
from atlas_preparation.infrastructure.repository import PreparationRepository, utcnow

logger = logging.getLogger("atlas.preparation")

CLEANING_STARTED = Counter("atlas_preparation_cleaning_started_total", "Cleaning jobs started")
CLEANING_COMPLETED = Counter(
    "atlas_preparation_cleaning_completed_total", "Cleaning jobs completed"
)
CLEANING_FAILED = Counter("atlas_preparation_cleaning_failed_total", "Cleaning jobs failed")
TRANSFORMATION_APPLIED = Counter(
    "atlas_preparation_transformation_applied_total", "Transformations applied"
)
APPROVAL_GRANTED = Counter("atlas_preparation_approval_granted_total", "Approvals granted")
APPROVAL_REJECTED = Counter("atlas_preparation_approval_rejected_total", "Approvals rejected")
RECIPE_GENERATED = Counter("atlas_preparation_recipe_generated_total", "Recipes generated")
ROWS_CLEANED = Counter("atlas_preparation_rows_cleaned_total", "Rows cleaned")
COLUMNS_MODIFIED = Counter("atlas_preparation_columns_modified_total", "Columns modified")
MISSING_FIXED = Counter("atlas_preparation_missing_fixed_total", "Missing values fixed")
DUPLICATES_REMOVED = Counter("atlas_preparation_duplicates_removed_total", "Duplicates removed")
CLEANING_DURATION = Histogram(
    "atlas_preparation_cleaning_duration_seconds",
    "Cleaning duration",
    buckets=(1, 5, 15, 60, 180, 600),
)


class PreparationService:
    """Human-in-the-loop data cleaning service.

    Flow:
    1. enqueue() creates a queued job
    2. run_job() analyzes data, generates recipe, sets status to awaiting_approval
    3. approve() applies recipe to data, creates new dataset version
    4. reject() marks job as rejected
    """

    def __init__(
        self,
        repo: PreparationRepository,
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
        strategies: dict[str, Any] | None = None,
    ) -> CleaningJobModel:
        """Queue a new cleaning job for analysis."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        dataset = self.catalog.get_dataset(org_id, dataset_id)
        if dataset is None or dataset.status == DatasetStatus.DELETED.value:
            raise NotFoundError("dataset not found")
        if dataset.status != DatasetStatus.READY.value:
            raise ForbiddenError("dataset is not ready for cleaning")

        job = CleaningJobModel(
            organization_id=org_id,
            dataset_id=dataset_id,
            dataset_version=dataset.current_version,
            status=JobStatus.QUEUED.value,
            progress=0,
            strategies=strategies or {},
            created_by_user_id=user_id,
        )
        self.repo.add_job(job)
        self.repo.session.flush()

        self.repo.add_history(org_id, job.id, "JobCreated", {"dataset_id": str(dataset_id)})

        logger.info(
            "JobCreated",
            extra={
                "tenant_id": str(org_id),
                "dataset_id": str(dataset_id),
                "job_id": str(job.id),
            },
        )
        return job

    def run_job(self, job_id: uuid.UUID) -> CleaningPlanModel:
        """Execute cleaning analysis (worker entrypoint).

        Generates a cleaning recipe and plan, sets status to AWAITING_APPROVAL.
        Does NOT create a new dataset version - that happens on approve().
        """
        import time

        started = time.perf_counter()

        job = self.repo.get_job_any(job_id)
        if job is None:
            raise NotFoundError("cleaning job not found")

        org_id = job.organization_id
        dataset_id = job.dataset_id

        job.status = JobStatus.RUNNING.value
        job.started_at = utcnow()
        job.progress = 5
        self.repo.session.flush()
        CLEANING_STARTED.inc()

        self.repo.add_history(org_id, job_id, "CleaningStarted")
        logger.info(
            "CleaningStarted",
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

            result = run_data_cleaning(df, profile, strategies=job.strategies)

            job.progress = 70
            RECIPE_GENERATED.inc()

            plan = CleaningPlanModel(
                organization_id=org_id,
                job_id=job.id,
                dataset_id=dataset_id,
                status=PlanStatus.DRAFT.value,
                summary=result["summary"],
                plan_json=result["plan"],
            )
            self.repo.add_plan(plan)

            recipe = CleaningRecipeModel(
                organization_id=org_id,
                job_id=job.id,
                plan_id=plan.id,
                version=1,
                recipe_json=result["recipe"],
            )
            self.repo.add_recipe(recipe)

            steps = result["recipe"].get("steps", [])
            for step_data in steps:
                step = CleaningStepModel(
                    organization_id=org_id,
                    recipe_id=recipe.id,
                    step_order=step_data.get("order", 0),
                    kind=step_data.get("kind", "unknown"),
                    column_name=step_data.get("column"),
                    params=step_data.get("params", {}),
                    reason=step_data.get("reason", ""),
                    expected_impact=step_data.get("expected_impact", ""),
                )
                self.repo.add_step(step)

            job.progress = 80

            report = CleaningReportModel(
                organization_id=org_id,
                job_id=job.id,
                summary=result["summary"],
                report_json={
                    "before": result["before"],
                    "after": result["after"],
                    "improvement": result["improvement"],
                    "step_count": len(steps),
                },
                graph_json=result["graph"],
            )
            self.repo.add_report(report)

            quality = QualityImprovementModel(
                organization_id=org_id,
                job_id=job.id,
                before_json=result["before"],
                after_json=result["after"],
                delta_json=result["improvement"],
                quality_before=float(result["before"].get("quality_overall", 0)),
                quality_after=float(result["after"].get("quality_overall", 0)),
            )
            self.repo.add_quality(quality)

            self.repo.add_history(
                org_id,
                job.id,
                "RecipeGenerated",
                {
                    "step_count": len(steps),
                    "quality_delta": result["improvement"].get("quality_delta"),
                },
            )

            job.progress = 90

            job.status = JobStatus.AWAITING_APPROVAL.value
            job.progress = 100
            job.completed_at = utcnow()

            CLEANING_DURATION.observe(time.perf_counter() - started)

            logger.info(
                "CleaningCompleted",
                extra={
                    "tenant_id": str(org_id),
                    "dataset_id": str(dataset_id),
                    "job_id": str(job_id),
                    "step_count": len(steps),
                },
            )

            return plan

        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.completed_at = utcnow()
            CLEANING_FAILED.inc()
            self.repo.add_history(org_id, job_id, "CleaningFailed", {"error": str(exc)[:500]})
            logger.exception("CleaningFailed", extra={"job_id": str(job_id)})
            raise

    def approve(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        job_id: uuid.UUID,
        edited_steps: list[dict[str, Any]] | None = None,
    ) -> PreparedDatasetModel:
        """Approve and apply the cleaning recipe.

        Creates a new dataset version with cleaned data.
        """
        self._require(user_id, org_id, Permission.PROJECT_WRITE)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("cleaning job not found")

        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError(f"job is not awaiting approval (status={job.status})")

        recipe = self.repo.get_recipe_by_job(org_id, job_id)
        if recipe is None:
            raise NotFoundError("recipe not found for job")

        plan = self.repo.get_plan_by_job(org_id, job_id)
        if plan is None:
            raise NotFoundError("plan not found for job")

        steps = edited_steps if edited_steps is not None else recipe.recipe_json.get("steps", [])

        if edited_steps is not None:
            recipe.recipe_json = {"version": recipe.recipe_json.get("version", 1), "steps": steps}
            self.repo.add_history(
                org_id,
                job_id,
                "RecipeEdited",
                {
                    "original_steps": len(recipe.recipe_json.get("steps", [])),
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

            before_snapshot = quality_snapshot(df)

            cleaned_df = apply_recipe(df, steps)

            after_snapshot = quality_snapshot(cleaned_df)

            csv_buffer = io.BytesIO()
            cleaned_df.to_csv(csv_buffer, index=False)
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
                original_filename=f"cleaned_{version.original_filename}",
                extension=".csv",
                mime_type="text/csv",
                encoding="utf-8",
                size_bytes=len(csv_bytes),
                checksum_sha256=checksum,
                row_estimate=after_snapshot["rows"],
                column_estimate=after_snapshot["columns"],
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
                row_estimate=after_snapshot["rows"],
                column_estimate=after_snapshot["columns"],
                size_bytes=len(csv_bytes),
                extra={"cleaned": True, "source_version": job.dataset_version},
            )
            self.catalog.add_stats(stats_record)

            self.catalog.add_lineage(
                DatasetLineageModel(
                    id=uuid7(),
                    organization_id=org_id,
                    dataset_id=dataset.id,
                    parent_dataset_id=dataset.id,
                    parent_version_id=version.id,
                    relation="cleaned_from",
                    metadata_json={
                        "job_id": str(job_id),
                        "source_version": job.dataset_version,
                        "output_version": new_version_no,
                        "steps": len(steps),
                    },
                )
            )

            dataset.current_version = new_version_no
            dataset.status = DatasetStatus.READY.value

            prepared = PreparedDatasetModel(
                organization_id=org_id,
                job_id=job_id,
                source_dataset_id=job.dataset_id,
                source_version=job.dataset_version,
                output_dataset_id=dataset.id,
                output_version=new_version_no,
                storage_key=storage_key,
                rows=after_snapshot["rows"],
                columns=after_snapshot["columns"],
            )
            self.repo.add_prepared(prepared)

            final_quality = QualityImprovementModel(
                organization_id=org_id,
                job_id=job_id,
                before_json=before_snapshot,
                after_json=after_snapshot,
                delta_json={
                    "missing_pct_delta": round(
                        before_snapshot["missing_pct"] - after_snapshot["missing_pct"], 4
                    ),
                    "duplicate_pct_delta": round(
                        before_snapshot["duplicate_pct"] - after_snapshot["duplicate_pct"], 4
                    ),
                    "quality_delta": round(
                        after_snapshot["quality_overall"] - before_snapshot["quality_overall"], 4
                    ),
                    "rows_delta": after_snapshot["rows"] - before_snapshot["rows"],
                    "columns_delta": after_snapshot["columns"] - before_snapshot["columns"],
                },
                quality_before=float(before_snapshot["quality_overall"]),
                quality_after=float(after_snapshot["quality_overall"]),
            )
            self.repo.add_quality(final_quality)

            plan.status = PlanStatus.APPROVED.value
            job.status = JobStatus.COMPLETED.value

            self.repo.add_history(
                org_id, job_id, "TransformationApplied", {"step_count": len(steps)}
            )
            self.repo.add_history(
                org_id,
                job_id,
                "ApprovalGranted",
                {
                    "user_id": str(user_id),
                    "output_version": new_version_no,
                    "quality_before": before_snapshot["quality_overall"],
                    "quality_after": after_snapshot["quality_overall"],
                },
            )

            APPROVAL_GRANTED.inc()
            TRANSFORMATION_APPLIED.inc(len(steps))
            CLEANING_COMPLETED.inc()
            ROWS_CLEANED.inc(after_snapshot["rows"])
            COLUMNS_MODIFIED.inc(abs(before_snapshot["columns"] - after_snapshot["columns"]))

            missing_fixed = int(
                (before_snapshot["missing_pct"] - after_snapshot["missing_pct"])
                / 100
                * before_snapshot["rows"]
                * before_snapshot["columns"]
            )
            if missing_fixed > 0:
                MISSING_FIXED.inc(missing_fixed)

            dups_removed = before_snapshot["duplicate_rows"] - after_snapshot.get(
                "duplicate_rows", 0
            )
            if dups_removed > 0:
                DUPLICATES_REMOVED.inc(dups_removed)

            logger.info(
                "ApprovalGranted",
                extra={
                    "tenant_id": str(org_id),
                    "job_id": str(job_id),
                    "user_id": str(user_id),
                    "output_version": new_version_no,
                },
            )

            # Commit before response so follow-up GETs see the new version
            # (FastAPI yield-deps commit after the response is sent).
            self.repo.session.commit()
            return prepared

        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.error_message = f"Apply failed: {exc}"[:2000]
            CLEANING_FAILED.inc()
            self.repo.add_history(org_id, job_id, "ApplyFailed", {"error": str(exc)[:500]})
            logger.exception("ApplyFailed", extra={"job_id": str(job_id)})
            raise

    def reject(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID, reason: str = ""
    ) -> CleaningJobModel:
        """Reject a cleaning job."""
        self._require(user_id, org_id, Permission.PROJECT_WRITE)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("cleaning job not found")

        if job.status != JobStatus.AWAITING_APPROVAL.value:
            raise ForbiddenError(f"job is not awaiting approval (status={job.status})")

        plan = self.repo.get_plan_by_job(org_id, job_id)
        if plan:
            plan.status = PlanStatus.REJECTED.value

        job.status = JobStatus.REJECTED.value
        job.error_message = reason[:2000] if reason else None

        self.repo.add_history(
            org_id, job_id, "ApprovalRejected", {"user_id": str(user_id), "reason": reason}
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
        """Get the latest cleaning summary for a dataset."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        job = self.repo.latest_job_for_dataset(org_id, dataset_id)
        if job is None:
            raise NotFoundError("no cleaning jobs found for dataset")

        plan = self.repo.get_plan_by_job(org_id, job.id)
        report = self.repo.get_report_by_job(org_id, job.id)
        recipe = self.repo.get_recipe_by_job(org_id, job.id)

        result: dict[str, Any] = {
            "dataset_id": dataset_id,
            "job_id": job.id,
            "status": job.status,
            "summary": plan.summary if plan else "",
        }

        if report:
            result["quality_before"] = report.report_json.get("before", {}).get("quality_overall")
            result["quality_after"] = report.report_json.get("after", {}).get("quality_overall")

        prepared = self.repo.session.query(PreparedDatasetModel).filter_by(job_id=job.id).first()
        if prepared:
            result["output_version"] = prepared.output_version

        if recipe:
            result["recipe_id"] = recipe.id

        if report:
            result["report_id"] = report.id

        return result

    def list_history(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """List transformation history for a dataset's cleaning jobs."""
        self._require(user_id, org_id, Permission.PROJECT_READ)
        jobs = [j for j in self.repo.list_jobs(org_id) if j.dataset_id == dataset_id]
        events: list[dict[str, Any]] = []
        for job in jobs:
            for row in self.repo.list_history(org_id, job.id):
                events.append(
                    {
                        "job_id": str(job.id),
                        "event_type": row.event,
                        "payload": row.detail,
                        "created_at": row.created_at.isoformat(),
                    }
                )
        events.sort(key=lambda e: e["created_at"])
        return events

    def get_recipe(
        self, user_id: uuid.UUID, org_id: uuid.UUID, recipe_id: uuid.UUID
    ) -> dict[str, Any]:
        """Get recipe details."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        recipe = self.repo.get_recipe(org_id, recipe_id)
        if recipe is None:
            raise NotFoundError("recipe not found")

        steps = self.repo.list_steps(recipe.id)

        return {
            "id": recipe.id,
            "job_id": recipe.job_id,
            "plan_id": recipe.plan_id,
            "version": recipe.version,
            "recipe_json": recipe.recipe_json,
            "steps": [
                {
                    "id": s.id,
                    "order": s.step_order,
                    "kind": s.kind,
                    "column": s.column_name,
                    "params": s.params,
                    "reason": s.reason,
                    "expected_impact": s.expected_impact,
                    "approved": s.approved,
                }
                for s in steps
            ],
            "created_at": recipe.created_at.isoformat(),
        }

    def get_report(
        self, user_id: uuid.UUID, org_id: uuid.UUID, report_id: uuid.UUID
    ) -> dict[str, Any]:
        """Get report details."""
        self._require(user_id, org_id, Permission.PROJECT_READ)

        report = self.repo.get_report(org_id, report_id)
        if report is None:
            raise NotFoundError("report not found")

        return {
            "id": report.id,
            "job_id": report.job_id,
            "summary": report.summary,
            "report_json": report.report_json,
            "graph_json": report.graph_json,
            "report": report.report_json,
            "graph": report.graph_json,
            "created_at": report.created_at.isoformat(),
        }

    def export(self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID) -> dict[str, Any]:
        """Export cleaned dataset or recipe.

        Returns presigned URL for the cleaned version or recipe JSON.
        """
        self._require(user_id, org_id, Permission.PROJECT_READ)

        job = self.repo.get_job(org_id, job_id)
        if job is None:
            raise NotFoundError("cleaning job not found")

        result: dict[str, Any] = {"job_id": job_id, "status": job.status}

        prepared = self.repo.session.query(PreparedDatasetModel).filter_by(job_id=job_id).first()
        if prepared:
            url = self.storage.presigned_url(
                self.bucket, prepared.storage_key, expires=timedelta(hours=1)
            )
            result["data_url"] = url
            result["expires_in_seconds"] = 3600

        recipe = self.repo.get_recipe_by_job(org_id, job_id)
        if recipe:
            result["recipe"] = recipe.recipe_json

        return result

"""Profiling application service."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import timedelta
from typing import Any

from atlas_catalog.domain import DatasetStatus
from atlas_catalog.infrastructure.repository import CatalogRepository
from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_identity.domain.rbac import OrgRole, Permission, has_permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_storage.ports import ObjectStorage
from prometheus_client import Counter, Histogram

from atlas_profiling.domain import JobStatus
from atlas_profiling.infrastructure.artifacts import (
    build_html,
    build_markdown,
    build_pdf,
    build_visualizations,
)
from atlas_profiling.infrastructure.loader import load_dataframe
from atlas_profiling.infrastructure.models import (
    ColumnProfileModel,
    ColumnStatisticsModel,
    DatasetProfileModel,
    LeakageReportModel,
    ProfilingArtifactModel,
    ProfilingJobModel,
    QualityReportModel,
)
from atlas_profiling.infrastructure.repository import ProfilingRepository, utcnow

logger = logging.getLogger("atlas.profiling")

PROFILING_STARTED = Counter("atlas_profiling_started_total", "Profiling jobs started")
PROFILING_COMPLETED = Counter("atlas_profiling_completed_total", "Profiling jobs completed")
PROFILING_FAILED = Counter("atlas_profiling_failed_total", "Profiling jobs failed")
TARGET_DETECTED = Counter("atlas_profiling_target_detected_total", "Targets inferred")
LEAKAGE_DETECTED = Counter("atlas_profiling_leakage_detected_total", "Leakage findings")
PROFILING_DURATION = Histogram(
    "atlas_profiling_duration_seconds", "Profiling duration", buckets=(1, 5, 15, 60, 180, 600)
)
ROWS_PROCESSED = Counter("atlas_profiling_rows_processed_total", "Rows processed")
COLS_PROCESSED = Counter("atlas_profiling_columns_processed_total", "Columns processed")


class ProfilingService:
    def __init__(
        self,
        repo: ProfilingRepository,
        catalog: CatalogRepository,
        identity: IdentityRepository,
        storage: ObjectStorage,
        *,
        bucket: str,
    ) -> None:
        self.repo = repo
        self.catalog = catalog
        self.identity = identity
        self.storage = storage
        self.bucket = bucket

    def _require(self, user_id: uuid.UUID, org_id: uuid.UUID, permission: Permission) -> None:
        membership = self.identity.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        if not has_permission(OrgRole(membership.role), permission):
            raise ForbiddenError(f"missing permission {permission.value}")

    def enqueue(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> ProfilingJobModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        dataset = self.catalog.get_dataset(org_id, dataset_id)
        if dataset is None or dataset.status == DatasetStatus.DELETED.value:
            raise NotFoundError("dataset not found")
        if dataset.status != DatasetStatus.READY.value:
            raise ForbiddenError("dataset is not ready for profiling")
        job = ProfilingJobModel(
            organization_id=org_id,
            dataset_id=dataset_id,
            dataset_version=dataset.current_version,
            status=JobStatus.QUEUED.value,
            progress=0,
            created_by_user_id=user_id,
        )
        self.repo.add_job(job)
        self.repo.session.flush()
        logger.info(
            "JobCreated",
            extra={"tenant_id": str(org_id), "dataset_id": str(dataset_id), "job_id": str(job.id)},
        )
        return job

    def run_job(self, job_id: uuid.UUID) -> DatasetProfileModel:
        """Execute profiling synchronously (worker entrypoint)."""
        import time

        started = time.perf_counter()
        job = self.repo.get_job_any(job_id)
        if job is None:
            raise NotFoundError("profiling job not found")
        org_id = job.organization_id
        dataset_id = job.dataset_id
        job.status = JobStatus.RUNNING.value
        job.started_at = utcnow()
        job.progress = 5
        self.repo.session.flush()
        PROFILING_STARTED.inc()
        logger.info(
            "ProfilingStarted",
            extra={"tenant_id": str(org_id), "dataset_id": str(dataset_id), "job_id": str(job.id)},
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
            job.progress = 35
            df = load_dataframe(raw, version.original_filename)
            job.progress = 50

            from atlas_contracts.agents import AgentRequest

            from atlas_profiling.application.agent import run_dataset_understanding

            response = run_dataset_understanding(
                AgentRequest(instructions="profile dataset"),
                dataframe=df,
                file_size_bytes=version.size_bytes,
            )
            profile = response.metadata["profile"]
            summary = profile.get("summary") or (response.messages[0] if response.messages else "")
            job.progress = 70

            if profile.get("target", {}).get("column"):
                TARGET_DETECTED.inc()
            if profile.get("leakage", {}).get("count"):
                LEAKAGE_DETECTED.inc(profile["leakage"]["count"])

            viz = build_visualizations(df.head(5000), profile)
            md = build_markdown(profile, summary)
            html = build_html(profile, summary, md)
            pdf = build_pdf(summary, profile)
            profile_bytes = json.dumps(profile, default=str).encode("utf-8")
            viz_bytes = json.dumps(viz, default=str).encode("utf-8")

            base = f"{org_id}/{dataset.project_id}/{dataset_id}/profiles/{job.id}"
            artifacts = [
                ("json", f"{base}/report.json", "application/json", profile_bytes),
                ("markdown", f"{base}/report.md", "text/markdown", md.encode("utf-8")),
                ("html", f"{base}/report.html", "text/html", html.encode("utf-8")),
                ("pdf", f"{base}/report.pdf", "application/pdf", pdf),
                ("plotly", f"{base}/visualizations.json", "application/json", viz_bytes),
            ]
            for _atype, key, ctype, payload in artifacts:
                self.storage.upload(self.bucket, key, payload, content_type=ctype)

            job.progress = 90
            row = DatasetProfileModel(
                organization_id=org_id,
                dataset_id=dataset_id,
                dataset_version=job.dataset_version,
                job_id=job.id,
                rows=int(profile["overview"]["rows"]),
                columns=int(profile["overview"]["columns"]),
                memory_bytes=int(profile["overview"]["memory_bytes"]),
                file_size_bytes=version.size_bytes,
                problem_type=profile["problem_type"],
                target_column=profile["target"].get("column"),
                target_confidence=profile["target"].get("confidence"),
                health=profile["quality"]["health"],
                quality_overall=float(profile["quality"]["overall"]),
                summary=summary,
                profile_json=profile,
            )
            self.repo.add_profile(row)
            for col in profile["columns"]:
                self.repo.add_column_profile(
                    ColumnProfileModel(
                        organization_id=org_id,
                        profile_id=row.id,
                        name=col["name"],
                        kind=col["kind"],
                        dtype=col["dtype"],
                        missing=col["missing"],
                        missing_pct=col["missing_pct"],
                        unique_count=col["unique"],
                        nearly_constant=bool(col.get("nearly_constant")),
                        details=col,
                    )
                )
                if col.get("statistics"):
                    self.repo.add_column_stats(
                        ColumnStatisticsModel(
                            organization_id=org_id,
                            profile_id=row.id,
                            column_name=col["name"],
                            statistics=col["statistics"],
                        )
                    )
            self.repo.add_quality(
                QualityReportModel(
                    organization_id=org_id, profile_id=row.id, report=profile["quality"]
                )
            )
            self.repo.add_leakage(
                LeakageReportModel(
                    organization_id=org_id, profile_id=row.id, report=profile["leakage"]
                )
            )
            for atype, key, ctype, payload in artifacts:
                self.repo.add_artifact(
                    ProfilingArtifactModel(
                        organization_id=org_id,
                        profile_id=row.id,
                        artifact_type=atype,
                        storage_key=key,
                        content_type=ctype,
                        size_bytes=len(payload),
                    )
                )

            job.status = JobStatus.COMPLETED.value
            job.progress = 100
            job.completed_at = utcnow()
            ROWS_PROCESSED.inc(row.rows)
            COLS_PROCESSED.inc(row.columns)
            PROFILING_COMPLETED.inc()
            PROFILING_DURATION.observe(time.perf_counter() - started)
            logger.info(
                "ProfilingFinished",
                extra={
                    "tenant_id": str(org_id),
                    "dataset_id": str(dataset_id),
                    "job_id": str(job.id),
                },
            )
            if profile["leakage"].get("findings"):
                logger.info(
                    "LeakageDetected",
                    extra={"tenant_id": str(org_id), "count": profile["leakage"]["count"]},
                )
            if profile["target"].get("column"):
                logger.info(
                    "TargetDetected",
                    extra={
                        "tenant_id": str(org_id),
                        "column": profile["target"]["column"],
                        "confidence": profile["target"]["confidence"],
                    },
                )
            return row
        except Exception as exc:
            job.status = JobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            job.completed_at = utcnow()
            PROFILING_FAILED.inc()
            logger.exception(
                "ProfilingFailed",
                extra={"job_id": str(job_id)},
            )
            raise

    def get_profile(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> dict[str, Any]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        profile = self.repo.get_latest_profile(org_id, dataset_id)
        if profile is None:
            raise NotFoundError("profile not found")
        return profile.profile_json

    def get_profile_row(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> DatasetProfileModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        profile = self.repo.get_latest_profile(org_id, dataset_id)
        if profile is None:
            raise NotFoundError("profile not found")
        return profile

    def download_artifact(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        dataset_id: uuid.UUID,
        artifact_type: str = "json",
    ) -> tuple[str, str]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        profile = self.repo.get_latest_profile(org_id, dataset_id)
        if profile is None:
            raise NotFoundError("profile not found")
        arts = self.repo.list_artifacts(profile.id)
        match = next((a for a in arts if a.artifact_type == artifact_type), None)
        if match is None:
            raise NotFoundError("artifact not found")
        url = self.storage.presigned_url(self.bucket, match.storage_key, expires=timedelta(hours=1))
        return url, match.content_type

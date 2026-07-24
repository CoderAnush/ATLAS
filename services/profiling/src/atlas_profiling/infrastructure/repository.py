"""Profiling repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas_profiling.infrastructure.models import (
    ColumnProfileModel,
    ColumnStatisticsModel,
    DatasetProfileModel,
    LeakageReportModel,
    ProfilingArtifactModel,
    ProfilingJobModel,
    QualityReportModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class ProfilingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, job: ProfilingJobModel) -> ProfilingJobModel:
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> ProfilingJobModel | None:
        return self.session.scalar(
            select(ProfilingJobModel).where(
                ProfilingJobModel.organization_id == org_id,
                ProfilingJobModel.id == job_id,
            )
        )

    def get_job_any(self, job_id: uuid.UUID) -> ProfilingJobModel | None:
        return self.session.scalar(select(ProfilingJobModel).where(ProfilingJobModel.id == job_id))

    def list_jobs(self, org_id: uuid.UUID, limit: int = 50) -> list[ProfilingJobModel]:
        return list(
            self.session.scalars(
                select(ProfilingJobModel)
                .where(ProfilingJobModel.organization_id == org_id)
                .order_by(ProfilingJobModel.created_at.desc())
                .limit(limit)
            ).all()
        )

    def get_latest_profile(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> DatasetProfileModel | None:
        return self.session.scalar(
            select(DatasetProfileModel)
            .where(
                DatasetProfileModel.organization_id == org_id,
                DatasetProfileModel.dataset_id == dataset_id,
            )
            .order_by(DatasetProfileModel.created_at.desc())
            .limit(1)
        )

    def add_profile(self, row: DatasetProfileModel) -> DatasetProfileModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_column_profile(self, row: ColumnProfileModel) -> None:
        self.session.add(row)

    def add_column_stats(self, row: ColumnStatisticsModel) -> None:
        self.session.add(row)

    def add_quality(self, row: QualityReportModel) -> None:
        self.session.add(row)

    def add_leakage(self, row: LeakageReportModel) -> None:
        self.session.add(row)

    def add_artifact(self, row: ProfilingArtifactModel) -> None:
        self.session.add(row)

    def list_artifacts(self, profile_id: uuid.UUID) -> list[ProfilingArtifactModel]:
        return list(
            self.session.scalars(
                select(ProfilingArtifactModel).where(ProfilingArtifactModel.profile_id == profile_id)
            ).all()
        )

    def list_columns(self, profile_id: uuid.UUID) -> list[ColumnProfileModel]:
        return list(
            self.session.scalars(
                select(ColumnProfileModel).where(ColumnProfileModel.profile_id == profile_id)
            ).all()
        )

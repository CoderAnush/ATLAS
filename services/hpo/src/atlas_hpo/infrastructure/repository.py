"""Repository helpers for the HPO bounded context."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

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
from sqlalchemy import select
from sqlalchemy.orm import Session


def utcnow() -> datetime:
    return datetime.now(UTC)


class HpoRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, row: OptimizationJobModel) -> None:
        self.session.add(row)
        self.session.flush()

    def add_study(self, row: OptimizationStudyModel) -> None:
        self.session.add(row)
        self.session.flush()

    def add_trial(self, row: OptimizationTrialModel) -> None:
        self.session.add(row)
        self.session.flush()

    def add_best_trial(self, row: BestTrialModel) -> None:
        self.session.add(row)
        self.session.flush()

    def add_config(self, row: OptimizationConfigModel) -> None:
        self.session.add(row)

    def add_metric(self, row: OptimizationMetricModel) -> None:
        self.session.add(row)

    def add_artifact(self, row: OptimizationArtifactModel) -> None:
        self.session.add(row)

    def add_log(self, row: OptimizationLogModel) -> None:
        self.session.add(row)

    def add_search_space(self, row: SearchSpaceModel) -> None:
        self.session.add(row)

    def add_tag(self, row: OptimizationTagModel) -> None:
        self.session.add(row)

    def get_job(self, org_id: UUID, job_id: UUID) -> OptimizationJobModel | None:
        return self.session.scalar(
            select(OptimizationJobModel).where(
                OptimizationJobModel.organization_id == org_id,
                OptimizationJobModel.id == job_id,
            )
        )

    def get_job_any(self, job_id: UUID) -> OptimizationJobModel | None:
        return self.session.scalar(select(OptimizationJobModel).where(OptimizationJobModel.id == job_id))

    def list_jobs(self, org_id: UUID) -> list[OptimizationJobModel]:
        return list(
            self.session.scalars(
                select(OptimizationJobModel)
                .where(OptimizationJobModel.organization_id == org_id)
                .order_by(OptimizationJobModel.created_at.desc())
            )
        )

    def get_study(self, org_id: UUID, study_id: UUID) -> OptimizationStudyModel | None:
        return self.session.scalar(
            select(OptimizationStudyModel).where(
                OptimizationStudyModel.organization_id == org_id,
                OptimizationStudyModel.id == study_id,
            )
        )

    def get_study_by_job(self, org_id: UUID, job_id: UUID) -> OptimizationStudyModel | None:
        return self.session.scalar(
            select(OptimizationStudyModel).where(
                OptimizationStudyModel.organization_id == org_id,
                OptimizationStudyModel.job_id == job_id,
            )
        )

    def list_studies(self, org_id: UUID) -> list[OptimizationStudyModel]:
        return list(
            self.session.scalars(
                select(OptimizationStudyModel)
                .where(OptimizationStudyModel.organization_id == org_id)
                .order_by(OptimizationStudyModel.created_at.desc())
            )
        )

    def list_trials(self, org_id: UUID, study_id: UUID) -> list[OptimizationTrialModel]:
        return list(
            self.session.scalars(
                select(OptimizationTrialModel)
                .where(
                    OptimizationTrialModel.organization_id == org_id,
                    OptimizationTrialModel.study_id == study_id,
                )
                .order_by(OptimizationTrialModel.trial_number.asc())
            )
        )

    def get_best_trial(self, study_id: UUID) -> BestTrialModel | None:
        return self.session.scalar(select(BestTrialModel).where(BestTrialModel.study_id == study_id))

    def list_metrics(self, org_id: UUID, study_id: UUID) -> list[OptimizationMetricModel]:
        return list(
            self.session.scalars(
                select(OptimizationMetricModel).where(
                    OptimizationMetricModel.organization_id == org_id,
                    OptimizationMetricModel.study_id == study_id,
                )
            )
        )

    def list_artifacts(self, org_id: UUID, study_id: UUID) -> list[OptimizationArtifactModel]:
        return list(
            self.session.scalars(
                select(OptimizationArtifactModel).where(
                    OptimizationArtifactModel.organization_id == org_id,
                    OptimizationArtifactModel.study_id == study_id,
                )
            )
        )

    def get_search_space(self, study_id: UUID) -> SearchSpaceModel | None:
        return self.session.scalar(select(SearchSpaceModel).where(SearchSpaceModel.study_id == study_id))

"""Preparation persistence repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas_preparation.infrastructure.models import (
    CleaningJobModel,
    CleaningPlanModel,
    CleaningRecipeModel,
    CleaningReportModel,
    CleaningStepModel,
    PreparedDatasetModel,
    QualityImprovementModel,
    TransformationHistoryModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class PreparationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, job: CleaningJobModel) -> CleaningJobModel:
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> CleaningJobModel | None:
        return self.session.scalar(
            select(CleaningJobModel).where(
                CleaningJobModel.organization_id == org_id, CleaningJobModel.id == job_id
            )
        )

    def get_job_any(self, job_id: uuid.UUID) -> CleaningJobModel | None:
        return self.session.get(CleaningJobModel, job_id)

    def list_jobs(self, org_id: uuid.UUID, limit: int = 50) -> list[CleaningJobModel]:
        return list(
            self.session.scalars(
                select(CleaningJobModel)
                .where(CleaningJobModel.organization_id == org_id)
                .order_by(CleaningJobModel.created_at.desc())
                .limit(limit)
            )
        )

    def latest_job_for_dataset(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> CleaningJobModel | None:
        return self.session.scalar(
            select(CleaningJobModel)
            .where(
                CleaningJobModel.organization_id == org_id,
                CleaningJobModel.dataset_id == dataset_id,
            )
            .order_by(CleaningJobModel.created_at.desc())
            .limit(1)
        )

    def add_plan(self, plan: CleaningPlanModel) -> CleaningPlanModel:
        self.session.add(plan)
        self.session.flush()
        return plan

    def get_plan_by_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> CleaningPlanModel | None:
        return self.session.scalar(
            select(CleaningPlanModel).where(
                CleaningPlanModel.organization_id == org_id, CleaningPlanModel.job_id == job_id
            )
        )

    def add_recipe(self, recipe: CleaningRecipeModel) -> CleaningRecipeModel:
        self.session.add(recipe)
        self.session.flush()
        return recipe

    def get_recipe(self, org_id: uuid.UUID, recipe_id: uuid.UUID) -> CleaningRecipeModel | None:
        return self.session.scalar(
            select(CleaningRecipeModel).where(
                CleaningRecipeModel.organization_id == org_id, CleaningRecipeModel.id == recipe_id
            )
        )

    def get_recipe_by_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> CleaningRecipeModel | None:
        return self.session.scalar(
            select(CleaningRecipeModel).where(
                CleaningRecipeModel.organization_id == org_id, CleaningRecipeModel.job_id == job_id
            )
        )

    def add_step(self, step: CleaningStepModel) -> CleaningStepModel:
        self.session.add(step)
        return step

    def list_steps(self, recipe_id: uuid.UUID) -> list[CleaningStepModel]:
        return list(
            self.session.scalars(
                select(CleaningStepModel)
                .where(CleaningStepModel.recipe_id == recipe_id)
                .order_by(CleaningStepModel.step_order.asc())
            )
        )

    def add_report(self, report: CleaningReportModel) -> CleaningReportModel:
        self.session.add(report)
        self.session.flush()
        return report

    def get_report(self, org_id: uuid.UUID, report_id: uuid.UUID) -> CleaningReportModel | None:
        return self.session.scalar(
            select(CleaningReportModel).where(
                CleaningReportModel.organization_id == org_id, CleaningReportModel.id == report_id
            )
        )

    def get_report_by_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> CleaningReportModel | None:
        return self.session.scalar(
            select(CleaningReportModel).where(
                CleaningReportModel.organization_id == org_id, CleaningReportModel.job_id == job_id
            )
        )

    def add_prepared(self, row: PreparedDatasetModel) -> PreparedDatasetModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_quality(self, row: QualityImprovementModel) -> QualityImprovementModel:
        self.session.add(row)
        return row

    def add_history(
        self, org_id: uuid.UUID, job_id: uuid.UUID, event: str, detail: dict[str, Any] | None = None
    ) -> TransformationHistoryModel:
        row = TransformationHistoryModel(
            organization_id=org_id, job_id=job_id, event=event, detail=detail or {}
        )
        self.session.add(row)
        return row

    def list_history(
        self, org_id: uuid.UUID, job_id: uuid.UUID
    ) -> list[TransformationHistoryModel]:
        return list(
            self.session.scalars(
                select(TransformationHistoryModel)
                .where(
                    TransformationHistoryModel.organization_id == org_id,
                    TransformationHistoryModel.job_id == job_id,
                )
                .order_by(TransformationHistoryModel.created_at.asc())
            )
        )

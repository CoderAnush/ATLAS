"""Modeling persistence repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas_modeling.infrastructure.models import (
    ModelTagModel,
    ModelVersionModel,
    TrainedModelModel,
    TrainingArtifactModel,
    TrainingConfigModel,
    TrainingJobModel,
    TrainingLineageModel,
    TrainingLogModel,
    TrainingMetricModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class ModelingRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, row: TrainingJobModel) -> TrainingJobModel:
        self.session.add(row)
        self.session.flush()
        return row

    def get_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> TrainingJobModel | None:
        return self.session.scalar(
            select(TrainingJobModel).where(
                TrainingJobModel.organization_id == org_id, TrainingJobModel.id == job_id
            )
        )

    def get_job_any(self, job_id: uuid.UUID) -> TrainingJobModel | None:
        return self.session.get(TrainingJobModel, job_id)

    def list_jobs(self, org_id: uuid.UUID, limit: int = 50) -> list[TrainingJobModel]:
        return list(
            self.session.scalars(
                select(TrainingJobModel)
                .where(TrainingJobModel.organization_id == org_id)
                .order_by(TrainingJobModel.created_at.desc())
                .limit(limit)
            )
        )

    def add_trained_model(self, row: TrainedModelModel) -> TrainedModelModel:
        self.session.add(row)
        self.session.flush()
        return row

    def get_model(self, org_id: uuid.UUID, model_id: uuid.UUID) -> TrainedModelModel | None:
        return self.session.scalar(
            select(TrainedModelModel).where(
                TrainedModelModel.organization_id == org_id, TrainedModelModel.id == model_id
            )
        )

    def get_model_by_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> TrainedModelModel | None:
        return self.session.scalar(
            select(TrainedModelModel).where(
                TrainedModelModel.organization_id == org_id, TrainedModelModel.job_id == job_id
            )
        )

    def list_models(self, org_id: uuid.UUID, limit: int = 50) -> list[TrainedModelModel]:
        return list(
            self.session.scalars(
                select(TrainedModelModel)
                .where(TrainedModelModel.organization_id == org_id)
                .order_by(TrainedModelModel.created_at.desc())
                .limit(limit)
            )
        )

    def add_version(self, row: ModelVersionModel) -> ModelVersionModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_metric(self, row: TrainingMetricModel) -> TrainingMetricModel:
        self.session.add(row)
        self.session.flush()
        return row

    def list_metrics(self, org_id: uuid.UUID, model_id: uuid.UUID) -> list[TrainingMetricModel]:
        return list(
            self.session.scalars(
                select(TrainingMetricModel)
                .where(
                    TrainingMetricModel.organization_id == org_id,
                    TrainingMetricModel.trained_model_id == model_id,
                )
                .order_by(TrainingMetricModel.created_at.asc())
            )
        )

    def add_artifact(self, row: TrainingArtifactModel) -> TrainingArtifactModel:
        self.session.add(row)
        self.session.flush()
        return row

    def list_artifacts(self, org_id: uuid.UUID, model_id: uuid.UUID) -> list[TrainingArtifactModel]:
        return list(
            self.session.scalars(
                select(TrainingArtifactModel)
                .where(
                    TrainingArtifactModel.organization_id == org_id,
                    TrainingArtifactModel.trained_model_id == model_id,
                )
                .order_by(TrainingArtifactModel.created_at.asc())
            )
        )

    def add_config(self, row: TrainingConfigModel) -> TrainingConfigModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_lineage(self, row: TrainingLineageModel) -> TrainingLineageModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_log(self, row: TrainingLogModel) -> TrainingLogModel:
        self.session.add(row)
        self.session.flush()
        return row

    def list_logs(self, org_id: uuid.UUID, job_id: uuid.UUID) -> list[TrainingLogModel]:
        return list(
            self.session.scalars(
                select(TrainingLogModel)
                .where(
                    TrainingLogModel.organization_id == org_id, TrainingLogModel.job_id == job_id
                )
                .order_by(TrainingLogModel.created_at.asc())
            )
        )

    def add_tag(self, row: ModelTagModel) -> ModelTagModel:
        self.session.add(row)
        self.session.flush()
        return row

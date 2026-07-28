"""Repository for experiment persistence."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Select, desc, or_, select
from sqlalchemy.orm import Session

from atlas_experiments.infrastructure.models import (
    ExperimentArtifactModel,
    ExperimentComparisonModel,
    ExperimentEnvironmentModel,
    ExperimentFavoriteModel,
    ExperimentHistoryModel,
    ExperimentLineageModel,
    ExperimentMetricModel,
    ExperimentModel,
    ExperimentNoteModel,
    ExperimentParameterModel,
    ExperimentRunModel,
    ExperimentTagModel,
    LeaderboardEntryModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class ExperimentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_experiment(self, row: ExperimentModel) -> ExperimentModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_run(self, row: ExperimentRunModel) -> ExperimentRunModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_metric(self, row: ExperimentMetricModel) -> None:
        self.session.add(row)

    def add_artifact(self, row: ExperimentArtifactModel) -> None:
        self.session.add(row)

    def add_parameter(self, row: ExperimentParameterModel) -> None:
        self.session.add(row)

    def add_environment(self, row: ExperimentEnvironmentModel) -> None:
        self.session.add(row)

    def add_tag(self, row: ExperimentTagModel) -> None:
        self.session.add(row)

    def add_note(self, row: ExperimentNoteModel) -> None:
        self.session.add(row)

    def add_lineage(self, row: ExperimentLineageModel) -> None:
        self.session.add(row)

    def add_comparison(self, row: ExperimentComparisonModel) -> None:
        self.session.add(row)

    def add_leaderboard(self, row: LeaderboardEntryModel) -> None:
        self.session.add(row)

    def add_favorite(self, row: ExperimentFavoriteModel) -> None:
        self.session.add(row)

    def add_history(self, row: ExperimentHistoryModel) -> None:
        self.session.add(row)

    def get_experiment(self, org_id: uuid.UUID, experiment_id: uuid.UUID) -> ExperimentModel | None:
        return self.session.scalar(
            select(ExperimentModel).where(
                ExperimentModel.organization_id == org_id,
                ExperimentModel.id == experiment_id,
            )
        )

    def get_run(self, org_id: uuid.UUID, run_id: uuid.UUID) -> ExperimentRunModel | None:
        return self.session.scalar(
            select(ExperimentRunModel).where(
                ExperimentRunModel.organization_id == org_id,
                ExperimentRunModel.id == run_id,
            )
        )

    def get_run_by_training_job(
        self, org_id: uuid.UUID, training_job_id: uuid.UUID
    ) -> ExperimentRunModel | None:
        return self.session.scalar(
            select(ExperimentRunModel).where(
                ExperimentRunModel.organization_id == org_id,
                ExperimentRunModel.training_job_id == training_job_id,
            )
        )

    def get_run_by_hpo_study(
        self, org_id: uuid.UUID, hpo_study_id: uuid.UUID
    ) -> ExperimentRunModel | None:
        return self.session.scalar(
            select(ExperimentRunModel).where(
                ExperimentRunModel.organization_id == org_id,
                ExperimentRunModel.hpo_study_id == hpo_study_id,
            )
        )

    def list_experiments(
        self, org_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> list[ExperimentModel]:
        stmt: Select[Any] = (
            select(ExperimentModel)
            .where(ExperimentModel.organization_id == org_id)
            .order_by(desc(ExperimentModel.created_at))
            .limit(limit)
            .offset(offset)
        )
        return list(self.session.scalars(stmt))

    def list_runs(
        self,
        org_id: uuid.UUID,
        *,
        experiment_id: uuid.UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExperimentRunModel]:
        stmt = select(ExperimentRunModel).where(ExperimentRunModel.organization_id == org_id)
        if experiment_id is not None:
            stmt = stmt.where(ExperimentRunModel.experiment_id == experiment_id)
        stmt = stmt.order_by(desc(ExperimentRunModel.created_at)).limit(limit).offset(offset)
        return list(self.session.scalars(stmt))

    def list_metrics(self, org_id: uuid.UUID, run_id: uuid.UUID) -> list[ExperimentMetricModel]:
        return list(
            self.session.scalars(
                select(ExperimentMetricModel).where(
                    ExperimentMetricModel.organization_id == org_id,
                    ExperimentMetricModel.run_id == run_id,
                )
            )
        )

    def list_artifacts(self, org_id: uuid.UUID, run_id: uuid.UUID) -> list[ExperimentArtifactModel]:
        return list(
            self.session.scalars(
                select(ExperimentArtifactModel).where(
                    ExperimentArtifactModel.organization_id == org_id,
                    ExperimentArtifactModel.run_id == run_id,
                )
            )
        )

    def list_history(
        self, org_id: uuid.UUID, experiment_id: uuid.UUID
    ) -> list[ExperimentHistoryModel]:
        return list(
            self.session.scalars(
                select(ExperimentHistoryModel)
                .where(
                    ExperimentHistoryModel.organization_id == org_id,
                    ExperimentHistoryModel.experiment_id == experiment_id,
                )
                .order_by(desc(ExperimentHistoryModel.created_at))
            )
        )

    def list_tags(self, org_id: uuid.UUID, experiment_id: uuid.UUID) -> list[ExperimentTagModel]:
        return list(
            self.session.scalars(
                select(ExperimentTagModel).where(
                    ExperimentTagModel.organization_id == org_id,
                    ExperimentTagModel.experiment_id == experiment_id,
                )
            )
        )

    def list_leaderboard(
        self, org_id: uuid.UUID, *, limit: int = 100, offset: int = 0
    ) -> list[LeaderboardEntryModel]:
        return list(
            self.session.scalars(
                select(LeaderboardEntryModel)
                .where(LeaderboardEntryModel.organization_id == org_id)
                .order_by(desc(LeaderboardEntryModel.rank_score))
                .limit(limit)
                .offset(offset)
            )
        )

    def search_experiments(
        self,
        org_id: uuid.UUID,
        *,
        query: str = "",
        algorithm: str | None = None,
        status: str | None = None,
        tag: str | None = None,
        owner_id: uuid.UUID | None = None,
        dataset_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[ExperimentModel]:
        stmt = select(ExperimentModel).where(ExperimentModel.organization_id == org_id)
        if query:
            like = f"%{query}%"
            stmt = stmt.where(
                or_(ExperimentModel.name.ilike(like), ExperimentModel.description.ilike(like))
            )
        if algorithm:
            stmt = stmt.where(ExperimentModel.algorithm == algorithm)
        if status:
            stmt = stmt.where(ExperimentModel.status == status)
        if owner_id:
            stmt = stmt.where(ExperimentModel.created_by_user_id == owner_id)
        if dataset_id:
            stmt = stmt.where(ExperimentModel.dataset_id == dataset_id)
        if tag:
            stmt = stmt.join(
                ExperimentTagModel,
                ExperimentTagModel.experiment_id == ExperimentModel.id,
            ).where(
                or_(
                    ExperimentTagModel.tag_key == tag,
                    ExperimentTagModel.tag_value == tag,
                )
            )
        stmt = stmt.order_by(desc(ExperimentModel.created_at)).limit(limit)
        return list(self.session.scalars(stmt).unique())

    def get_leaderboard_for_run(
        self, org_id: uuid.UUID, run_id: uuid.UUID
    ) -> LeaderboardEntryModel | None:
        return self.session.scalar(
            select(LeaderboardEntryModel).where(
                LeaderboardEntryModel.organization_id == org_id,
                LeaderboardEntryModel.run_id == run_id,
            )
        )

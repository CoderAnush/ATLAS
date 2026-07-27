"""Feature store persistence repository."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from atlas_feature_store.infrastructure.models import (
    FeatureJobModel,
    FeatureLineageModel,
    FeatureMetadataModel,
    FeatureRegistryModel,
    FeatureSetModel,
    FeatureStatisticsModel,
    FeatureTagModel,
    FeatureTransformationModel,
    FeatureVersionModel,
    FeatureViewModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class FeatureStoreRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_job(self, job: FeatureJobModel) -> FeatureJobModel:
        self.session.add(job)
        self.session.flush()
        return job

    def get_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> FeatureJobModel | None:
        return self.session.scalar(
            select(FeatureJobModel).where(
                FeatureJobModel.organization_id == org_id, FeatureJobModel.id == job_id
            )
        )

    def get_job_any(self, job_id: uuid.UUID) -> FeatureJobModel | None:
        return self.session.get(FeatureJobModel, job_id)

    def list_jobs(self, org_id: uuid.UUID, limit: int = 50) -> list[FeatureJobModel]:
        return list(
            self.session.scalars(
                select(FeatureJobModel)
                .where(FeatureJobModel.organization_id == org_id)
                .order_by(FeatureJobModel.created_at.desc())
                .limit(limit)
            )
        )

    def latest_job_for_dataset(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> FeatureJobModel | None:
        return self.session.scalar(
            select(FeatureJobModel)
            .where(
                FeatureJobModel.organization_id == org_id,
                FeatureJobModel.dataset_id == dataset_id,
            )
            .order_by(FeatureJobModel.created_at.desc())
            .limit(1)
        )

    def add_feature_set(self, feature_set: FeatureSetModel) -> FeatureSetModel:
        self.session.add(feature_set)
        self.session.flush()
        return feature_set

    def get_feature_set(
        self, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> FeatureSetModel | None:
        return self.session.scalar(
            select(FeatureSetModel).where(
                FeatureSetModel.organization_id == org_id,
                FeatureSetModel.id == feature_set_id,
            )
        )

    def get_feature_set_by_job(
        self, org_id: uuid.UUID, job_id: uuid.UUID
    ) -> FeatureSetModel | None:
        return self.session.scalar(
            select(FeatureSetModel).where(
                FeatureSetModel.organization_id == org_id, FeatureSetModel.job_id == job_id
            )
        )

    def list_feature_sets(self, org_id: uuid.UUID, limit: int = 50) -> list[FeatureSetModel]:
        return list(
            self.session.scalars(
                select(FeatureSetModel)
                .where(FeatureSetModel.organization_id == org_id)
                .order_by(FeatureSetModel.created_at.desc())
                .limit(limit)
            )
        )

    def search_feature_sets(
        self,
        org_id: uuid.UUID,
        query: str,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[FeatureSetModel]:
        stmt = select(FeatureSetModel).where(FeatureSetModel.organization_id == org_id)
        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                FeatureSetModel.name.ilike(pattern) | FeatureSetModel.summary.ilike(pattern)
            )
        if tags:
            stmt = (
                stmt.join(
                    FeatureRegistryModel,
                    FeatureRegistryModel.feature_set_id == FeatureSetModel.id,
                )
                .join(FeatureTagModel, FeatureTagModel.feature_id == FeatureRegistryModel.id)
                .where(FeatureTagModel.tag.in_(tags))
                .distinct()
            )
        stmt = stmt.order_by(FeatureSetModel.created_at.desc()).limit(limit)
        return list(self.session.scalars(stmt))

    def add_version(self, version: FeatureVersionModel) -> FeatureVersionModel:
        self.session.add(version)
        self.session.flush()
        return version

    def list_versions(
        self, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> list[FeatureVersionModel]:
        return list(
            self.session.scalars(
                select(FeatureVersionModel)
                .where(
                    FeatureVersionModel.organization_id == org_id,
                    FeatureVersionModel.feature_set_id == feature_set_id,
                )
                .order_by(FeatureVersionModel.version.desc())
            )
        )

    def get_version(self, org_id: uuid.UUID, version_id: uuid.UUID) -> FeatureVersionModel | None:
        return self.session.scalar(
            select(FeatureVersionModel).where(
                FeatureVersionModel.organization_id == org_id,
                FeatureVersionModel.id == version_id,
            )
        )

    def add_view(self, view: FeatureViewModel) -> FeatureViewModel:
        self.session.add(view)
        self.session.flush()
        return view

    def list_views(self, org_id: uuid.UUID, limit: int = 50) -> list[FeatureViewModel]:
        return list(
            self.session.scalars(
                select(FeatureViewModel)
                .where(FeatureViewModel.organization_id == org_id)
                .order_by(FeatureViewModel.created_at.desc())
                .limit(limit)
            )
        )

    def add_registry_feature(self, feature: FeatureRegistryModel) -> FeatureRegistryModel:
        self.session.add(feature)
        self.session.flush()
        return feature

    def list_registry(self, org_id: uuid.UUID, limit: int = 200) -> list[FeatureRegistryModel]:
        return list(
            self.session.scalars(
                select(FeatureRegistryModel)
                .where(FeatureRegistryModel.organization_id == org_id)
                .order_by(FeatureRegistryModel.created_at.asc())
                .limit(limit)
            )
        )

    def get_registry_feature(
        self, org_id: uuid.UUID, feature_id: uuid.UUID
    ) -> FeatureRegistryModel | None:
        return self.session.scalar(
            select(FeatureRegistryModel).where(
                FeatureRegistryModel.organization_id == org_id,
                FeatureRegistryModel.id == feature_id,
            )
        )

    def add_lineage(self, lineage: FeatureLineageModel) -> FeatureLineageModel:
        self.session.add(lineage)
        self.session.flush()
        return lineage

    def list_lineage_for_set(
        self, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> list[FeatureLineageModel]:
        return list(
            self.session.scalars(
                select(FeatureLineageModel)
                .where(
                    FeatureLineageModel.organization_id == org_id,
                    FeatureLineageModel.feature_set_id == feature_set_id,
                )
                .order_by(FeatureLineageModel.created_at.asc())
            )
        )

    def add_metadata(self, metadata: FeatureMetadataModel) -> FeatureMetadataModel:
        self.session.add(metadata)
        self.session.flush()
        return metadata

    def add_tag(self, tag: FeatureTagModel) -> FeatureTagModel:
        self.session.add(tag)
        self.session.flush()
        return tag

    def list_tags(self, org_id: uuid.UUID, feature_id: uuid.UUID) -> list[FeatureTagModel]:
        return list(
            self.session.scalars(
                select(FeatureTagModel)
                .where(
                    FeatureTagModel.organization_id == org_id,
                    FeatureTagModel.feature_id == feature_id,
                )
                .order_by(FeatureTagModel.created_at.asc())
            )
        )

    def add_statistics(self, stats: FeatureStatisticsModel) -> FeatureStatisticsModel:
        self.session.add(stats)
        self.session.flush()
        return stats

    def add_transformation(
        self, transformation: FeatureTransformationModel
    ) -> FeatureTransformationModel:
        self.session.add(transformation)
        self.session.flush()
        return transformation

    def list_transformations(
        self, org_id: uuid.UUID, feature_set_id: uuid.UUID
    ) -> list[FeatureTransformationModel]:
        return list(
            self.session.scalars(
                select(FeatureTransformationModel)
                .where(
                    FeatureTransformationModel.organization_id == org_id,
                    FeatureTransformationModel.feature_set_id == feature_set_id,
                )
                .order_by(FeatureTransformationModel.step_order.asc())
            )
        )

    def append_history(
        self, job: FeatureJobModel, event: str, detail: dict[str, Any] | None = None
    ) -> FeatureJobModel:
        history = list(job.history_json or [])
        history.append({"event": event, "detail": detail or {}, "at": utcnow().isoformat()})
        job.history_json = history
        self.session.flush()
        return job

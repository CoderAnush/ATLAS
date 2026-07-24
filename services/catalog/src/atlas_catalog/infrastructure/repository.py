"""Tenant-scoped catalog repository."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy import Select, and_, func, or_, select
from sqlalchemy.orm import Session

from atlas_catalog.domain import DatasetStatus
from atlas_catalog.infrastructure.models import (
    CatalogProjectModel,
    DatasetCommentModel,
    DatasetConnectorModel,
    DatasetDownloadLogModel,
    DatasetFavoriteModel,
    DatasetLineageModel,
    DatasetModel,
    DatasetPermissionModel,
    DatasetStatisticsModel,
    DatasetStorageModel,
    DatasetTagModel,
    DatasetUploadJobModel,
    DatasetVersionModel,
)


def utcnow() -> datetime:
    return datetime.now(UTC)


class CatalogRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    # --- projects ---
    def add_project(self, project: CatalogProjectModel) -> CatalogProjectModel:
        self.session.add(project)
        self.session.flush()
        return project

    def get_project(self, org_id: uuid.UUID, project_id: uuid.UUID) -> CatalogProjectModel | None:
        return self.session.scalar(
            select(CatalogProjectModel).where(
                CatalogProjectModel.organization_id == org_id,
                CatalogProjectModel.id == project_id,
            )
        )

    def list_projects(
        self, org_id: uuid.UUID, *, include_archived: bool = False
    ) -> list[CatalogProjectModel]:
        stmt: Select[tuple[CatalogProjectModel]] = select(CatalogProjectModel).where(
            CatalogProjectModel.organization_id == org_id
        )
        if not include_archived:
            stmt = stmt.where(CatalogProjectModel.is_archived.is_(False))
        stmt = stmt.order_by(CatalogProjectModel.created_at.desc())
        return list(self.session.scalars(stmt).all())

    # --- datasets ---
    def add_dataset(self, dataset: DatasetModel) -> DatasetModel:
        self.session.add(dataset)
        self.session.flush()
        return dataset

    def get_dataset(self, org_id: uuid.UUID, dataset_id: uuid.UUID) -> DatasetModel | None:
        return self.session.scalar(
            select(DatasetModel).where(
                DatasetModel.organization_id == org_id,
                DatasetModel.id == dataset_id,
            )
        )

    def find_duplicate_checksum(
        self, org_id: uuid.UUID, project_id: uuid.UUID, checksum: str
    ) -> DatasetVersionModel | None:
        return self.session.scalar(
            select(DatasetVersionModel)
            .join(DatasetModel, DatasetModel.id == DatasetVersionModel.dataset_id)
            .where(
                DatasetVersionModel.organization_id == org_id,
                DatasetModel.project_id == project_id,
                DatasetVersionModel.checksum_sha256 == checksum,
                DatasetModel.status != DatasetStatus.DELETED.value,
            )
            .limit(1)
        )

    def add_version(self, version: DatasetVersionModel) -> DatasetVersionModel:
        self.session.add(version)
        self.session.flush()
        return version

    def list_versions(self, org_id: uuid.UUID, dataset_id: uuid.UUID) -> list[DatasetVersionModel]:
        return list(
            self.session.scalars(
                select(DatasetVersionModel)
                .where(
                    DatasetVersionModel.organization_id == org_id,
                    DatasetVersionModel.dataset_id == dataset_id,
                )
                .order_by(DatasetVersionModel.version.desc())
            ).all()
        )

    def get_version(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID, version: int
    ) -> DatasetVersionModel | None:
        return self.session.scalar(
            select(DatasetVersionModel).where(
                DatasetVersionModel.organization_id == org_id,
                DatasetVersionModel.dataset_id == dataset_id,
                DatasetVersionModel.version == version,
            )
        )

    def add_storage(self, row: DatasetStorageModel) -> DatasetStorageModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_stats(self, row: DatasetStatisticsModel) -> DatasetStatisticsModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_tag(self, row: DatasetTagModel) -> DatasetTagModel:
        self.session.add(row)
        self.session.flush()
        return row

    def list_tags(self, dataset_id: uuid.UUID) -> list[DatasetTagModel]:
        return list(
            self.session.scalars(
                select(DatasetTagModel).where(DatasetTagModel.dataset_id == dataset_id)
            ).all()
        )

    def add_permission(self, row: DatasetPermissionModel) -> DatasetPermissionModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_upload_job(self, job: DatasetUploadJobModel) -> DatasetUploadJobModel:
        self.session.add(job)
        self.session.flush()
        return job

    def get_upload_job(self, org_id: uuid.UUID, job_id: uuid.UUID) -> DatasetUploadJobModel | None:
        return self.session.scalar(
            select(DatasetUploadJobModel).where(
                DatasetUploadJobModel.organization_id == org_id,
                DatasetUploadJobModel.id == job_id,
            )
        )

    def add_connector(self, row: DatasetConnectorModel) -> DatasetConnectorModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_lineage(self, row: DatasetLineageModel) -> DatasetLineageModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_download_log(self, row: DatasetDownloadLogModel) -> DatasetDownloadLogModel:
        self.session.add(row)
        self.session.flush()
        return row

    def add_favorite(self, row: DatasetFavoriteModel) -> DatasetFavoriteModel:
        self.session.add(row)
        self.session.flush()
        return row

    def get_favorite(
        self, org_id: uuid.UUID, dataset_id: uuid.UUID, user_id: uuid.UUID
    ) -> DatasetFavoriteModel | None:
        return self.session.scalar(
            select(DatasetFavoriteModel).where(
                DatasetFavoriteModel.organization_id == org_id,
                DatasetFavoriteModel.dataset_id == dataset_id,
                DatasetFavoriteModel.user_id == user_id,
            )
        )

    def delete_favorite(self, fav: DatasetFavoriteModel) -> None:
        self.session.delete(fav)

    def add_comment(self, row: DatasetCommentModel) -> DatasetCommentModel:
        self.session.add(row)
        self.session.flush()
        return row

    def search_datasets(
        self,
        org_id: uuid.UUID,
        *,
        q: str | None = None,
        project_id: uuid.UUID | None = None,
        tag: str | None = None,
        owner_id: uuid.UUID | None = None,
        dataset_format: str | None = None,
        favorite_user_id: uuid.UUID | None = None,
        uploaded_after: datetime | None = None,
        uploaded_before: datetime | None = None,
        include_deleted: bool = False,
        sort: str = "newest",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[DatasetModel], int]:
        stmt = select(DatasetModel).where(DatasetModel.organization_id == org_id)
        if not include_deleted:
            stmt = stmt.where(DatasetModel.status != DatasetStatus.DELETED.value)
        if project_id is not None:
            stmt = stmt.where(DatasetModel.project_id == project_id)
        if owner_id is not None:
            stmt = stmt.where(DatasetModel.created_by_user_id == owner_id)
        if dataset_format is not None:
            stmt = stmt.where(DatasetModel.format == dataset_format)
        if uploaded_after is not None:
            stmt = stmt.where(DatasetModel.created_at >= uploaded_after)
        if uploaded_before is not None:
            stmt = stmt.where(DatasetModel.created_at <= uploaded_before)
        if q:
            like = f"%{q.lower()}%"
            stmt = stmt.where(
                or_(
                    func.lower(DatasetModel.name).like(like),
                    func.lower(DatasetModel.original_filename).like(like),
                )
            )
        if tag:
            stmt = stmt.join(DatasetTagModel, DatasetTagModel.dataset_id == DatasetModel.id).where(
                DatasetTagModel.tag == tag
            )
        if favorite_user_id is not None:
            stmt = stmt.join(
                DatasetFavoriteModel, DatasetFavoriteModel.dataset_id == DatasetModel.id
            ).where(DatasetFavoriteModel.user_id == favorite_user_id)

        count_stmt = select(func.count()).select_from(stmt.order_by(None).subquery())
        total = int(self.session.scalar(count_stmt) or 0)

        order: Any = {
            "newest": DatasetModel.created_at.desc(),
            "oldest": DatasetModel.created_at.asc(),
            "most_recent": DatasetModel.updated_at.desc(),
            "most_downloaded": DatasetModel.download_count.desc(),
        }.get(sort, DatasetModel.created_at.desc())

        # size sorts need latest version size — approximate via current_version join later;
        # for largest/smallest use a correlated subquery on versions.
        if sort in {"largest", "smallest"}:
            size_sq = (
                select(DatasetVersionModel.size_bytes)
                .where(
                    and_(
                        DatasetVersionModel.dataset_id == DatasetModel.id,
                        DatasetVersionModel.version == DatasetModel.current_version,
                    )
                )
                .correlate(DatasetModel)
                .scalar_subquery()
            )
            order = size_sq.desc() if sort == "largest" else size_sq.asc()

        rows = list(
            self.session.scalars(stmt.order_by(cast(Any, order)).limit(limit).offset(offset)).all()
        )
        return rows, total

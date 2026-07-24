"""Catalog use cases: projects, uploads, versioning, search."""

from __future__ import annotations

import logging
import re
import tempfile
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO

from atlas_core.errors import ForbiddenError, NotFoundError
from atlas_core.ids import uuid7
from atlas_identity.domain.rbac import Permission
from atlas_identity.infrastructure.repository import IdentityRepository
from atlas_storage.ports import ObjectStorage
from atlas_telemetry.metrics import REQUEST_COUNT  # noqa: F401 — ensure metrics module loaded
from prometheus_client import Counter

from atlas_catalog.domain import (
    ConflictError,
    DatasetFormat,
    DatasetStatus,
    UploadJobStatus,
    ValidationError,
)
from atlas_catalog.domain.validation import (
    detect_text_encoding,
    extension_of,
    format_of,
    sanitize_filename,
    sha256_fileobj,
    sniff_magic,
    validate_mime,
    validate_size,
    validate_zip_safety,
)
from atlas_catalog.infrastructure.estimates import estimate_shape
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
from atlas_catalog.infrastructure.repository import CatalogRepository

logger = logging.getLogger("atlas.catalog")

DATASET_UPLOADED = Counter(
    "atlas_dataset_uploaded_total", "Datasets uploaded", ["format", "status"]
)
DATASET_DOWNLOADED = Counter("atlas_dataset_downloaded_total", "Dataset downloads")
DATASET_DELETED = Counter("atlas_dataset_deleted_total", "Datasets deleted")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (slug or "item")[:120]


def utcnow() -> datetime:
    return datetime.now(UTC)


class CatalogService:
    def __init__(
        self,
        repo: CatalogRepository,
        identity_repo: IdentityRepository,
        storage: ObjectStorage,
        *,
        bucket: str,
        max_upload_bytes: int,
    ) -> None:
        self.repo = repo
        self.identity = identity_repo
        self.storage = storage
        self.bucket = bucket
        self.max_upload_bytes = max_upload_bytes

    def _require(self, user_id: uuid.UUID, org_id: uuid.UUID, permission: Permission) -> None:
        membership = self.identity.get_membership(org_id, user_id)
        if membership is None:
            raise ForbiddenError("not a member of this organization")
        from atlas_identity.domain.rbac import OrgRole, has_permission

        if not has_permission(OrgRole(membership.role), permission):
            raise ForbiddenError(f"missing permission {permission.value}")

    # ---------- projects ----------
    def create_project(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        name: str,
        slug: str | None,
        description: str,
        tags: list[str],
    ) -> CatalogProjectModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        project = CatalogProjectModel(
            organization_id=org_id,
            name=name.strip(),
            slug=_slugify(slug or name),
            description=description,
            owner_user_id=user_id,
            tags=tags,
        )
        self.repo.add_project(project)
        logger.info(
            "ProjectCreated",
            extra={"tenant_id": str(org_id), "project_id": str(project.id), "user_id": str(user_id)},
        )
        return project

    def list_projects(self, user_id: uuid.UUID, org_id: uuid.UUID) -> list[CatalogProjectModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        return self.repo.list_projects(org_id)

    def get_project(self, user_id: uuid.UUID, org_id: uuid.UUID, project_id: uuid.UUID) -> CatalogProjectModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        project = self.repo.get_project(org_id, project_id)
        if project is None:
            raise NotFoundError("project not found")
        return project

    def update_project(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        *,
        name: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        is_archived: bool | None = None,
    ) -> CatalogProjectModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        project = self.get_project(user_id, org_id, project_id)
        if name is not None:
            project.name = name.strip()
        if description is not None:
            project.description = description
        if tags is not None:
            project.tags = tags
        if is_archived is not None:
            project.is_archived = is_archived
        project.updated_at = utcnow()
        return project

    def delete_project(self, user_id: uuid.UUID, org_id: uuid.UUID, project_id: uuid.UUID) -> None:
        self._require(user_id, org_id, Permission.PROJECT_DELETE)
        project = self.get_project(user_id, org_id, project_id)
        project.is_archived = True
        project.updated_at = utcnow()

    # ---------- upload core ----------
    def _object_key(
        self, org_id: uuid.UUID, project_id: uuid.UUID, dataset_id: uuid.UUID, version: int, file_uuid: str
    ) -> str:
        return f"{org_id}/{project_id}/{dataset_id}/{version}/{file_uuid}"

    def _finalize_from_path(
        self,
        *,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        path: Path,
        original_filename: str,
        content_type: str | None,
        dataset_id: uuid.UUID | None,
        name: str | None,
        description: str,
        tags: list[str],
        parent_dataset_id: uuid.UUID | None,
    ) -> DatasetModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        project = self.repo.get_project(org_id, project_id)
        if project is None:
            raise NotFoundError("project not found")

        safe_name = sanitize_filename(original_filename)
        ext = extension_of(safe_name)
        fmt = format_of(safe_name)
        size = path.stat().st_size
        validate_size(size, self.max_upload_bytes)
        mime = validate_mime(ext, content_type)

        with path.open("rb") as fh:
            head = fh.read(16)
            fh.seek(0)
            sniff_magic(ext, head)
            checksum = sha256_fileobj(fh)

        if fmt is DatasetFormat.ZIP:
            validate_zip_safety(str(path))

        encoding: str | None = None
        if fmt in {DatasetFormat.CSV, DatasetFormat.TSV, DatasetFormat.JSON}:
            with path.open("rb") as fh:
                encoding = detect_text_encoding(fh.read(64 * 1024))

        dup = self.repo.find_duplicate_checksum(org_id, project_id, checksum)
        if dup is not None and dataset_id is None:
            raise ConflictError("duplicate upload: identical checksum already exists in project")

        creating = dataset_id is None
        if creating:
            dataset = DatasetModel(
                organization_id=org_id,
                project_id=project_id,
                name=(name or Path(safe_name).stem)[:255],
                slug=_slugify(name or Path(safe_name).stem),
                description=description,
                status=DatasetStatus.VALIDATING.value,
                format=fmt.value,
                original_filename=safe_name,
                created_by_user_id=user_id,
                current_version=0,
            )
            self.repo.add_dataset(dataset)
            self.repo.add_permission(
                DatasetPermissionModel(
                    organization_id=org_id,
                    dataset_id=dataset.id,
                    user_id=user_id,
                    role="owner",
                )
            )
            for tag in tags:
                self.repo.add_tag(
                    DatasetTagModel(organization_id=org_id, dataset_id=dataset.id, tag=tag[:64])
                )
            if parent_dataset_id is not None:
                self.repo.add_lineage(
                    DatasetLineageModel(
                        organization_id=org_id,
                        dataset_id=dataset.id,
                        parent_dataset_id=parent_dataset_id,
                        relation="derived_from",
                    )
                )
        else:
            existing = self.repo.get_dataset(org_id, dataset_id)  # type: ignore[arg-type]
            if existing is None or existing.project_id != project_id:
                raise NotFoundError("dataset not found")
            if existing.status == DatasetStatus.DELETED.value:
                raise ConflictError("cannot version a deleted dataset")
            dataset = existing
            dataset.status = DatasetStatus.VALIDATING.value

        version_no = dataset.current_version + 1
        file_uuid = str(uuid7())
        storage_filename = f"{file_uuid}{ext}"
        object_key = self._object_key(org_id, project_id, dataset.id, version_no, storage_filename)

        version = DatasetVersionModel(
            organization_id=org_id,
            dataset_id=dataset.id,
            version=version_no,
            status=DatasetStatus.UPLOADING.value,
            storage_key=object_key,
            storage_filename=storage_filename,
            original_filename=safe_name,
            extension=ext,
            mime_type=mime,
            encoding=encoding,
            size_bytes=size,
            checksum_sha256=checksum,
            uploaded_by_user_id=user_id,
        )
        self.repo.add_version(version)

        logger.info(
            "DatasetValidated",
            extra={
                "tenant_id": str(org_id),
                "dataset_id": str(dataset.id),
                "checksum": checksum,
                "format": fmt.value,
            },
        )

        try:
            with path.open("rb") as fh:
                self.storage.upload_stream(
                    self.bucket, object_key, fh, length=size, content_type=mime
                )
            logger.info(
                "DatasetStored",
                extra={"tenant_id": str(org_id), "dataset_id": str(dataset.id), "key": object_key},
            )
            rows, cols = estimate_shape(path, fmt, encoding)
            version.row_estimate = rows
            version.column_estimate = cols
            version.status = DatasetStatus.READY.value
            dataset.status = DatasetStatus.READY.value
            dataset.current_version = version_no
            dataset.original_filename = safe_name
            dataset.format = fmt.value
            dataset.updated_at = utcnow()
            self.repo.add_storage(
                DatasetStorageModel(
                    organization_id=org_id,
                    dataset_version_id=version.id,
                    bucket=self.bucket,
                    object_key=object_key,
                )
            )
            self.repo.add_stats(
                DatasetStatisticsModel(
                    organization_id=org_id,
                    dataset_version_id=version.id,
                    row_estimate=rows,
                    column_estimate=cols,
                    size_bytes=size,
                )
            )
            DATASET_UPLOADED.labels(format=fmt.value, status="ready").inc()
            logger.info(
                "DatasetUploaded",
                extra={
                    "tenant_id": str(org_id),
                    "dataset_id": str(dataset.id),
                    "version": version_no,
                },
            )
        except Exception as exc:  # noqa: BLE001
            version.status = DatasetStatus.FAILED.value
            version.error_message = str(exc)[:2000]
            dataset.status = DatasetStatus.FAILED.value
            DATASET_UPLOADED.labels(format=fmt.value, status="failed").inc()
            logger.exception("Dataset upload failed")
            raise ValidationError(f"storage failed: {exc}") from exc

        return dataset

    def upload_stream(
        self,
        *,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        filename: str,
        stream: BinaryIO,
        size: int | None,
        content_type: str | None,
        dataset_id: uuid.UUID | None = None,
        name: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
        parent_dataset_id: uuid.UUID | None = None,
    ) -> DatasetModel:
        """Spool stream to temp file (disk-backed) then finalize — never hold whole file in RAM."""
        if size is not None:
            validate_size(size, self.max_upload_bytes)
        safe = sanitize_filename(filename)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(safe).suffix)
        tmp_path = Path(tmp.name)
        received = 0
        try:
            with tmp:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    received += len(chunk)
                    if received > self.max_upload_bytes:
                        raise ValidationError("file exceeds maximum upload size")
                    tmp.write(chunk)
            if received == 0:
                raise ValidationError("empty file rejected")
            return self._finalize_from_path(
                user_id=user_id,
                org_id=org_id,
                project_id=project_id,
                path=tmp_path,
                original_filename=safe,
                content_type=content_type,
                dataset_id=dataset_id,
                name=name,
                description=description,
                tags=tags or [],
                parent_dataset_id=parent_dataset_id,
            )
        finally:
            tmp_path.unlink(missing_ok=True)

    def init_multipart_upload(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        project_id: uuid.UUID,
        filename: str,
        content_type: str | None,
        expected_size: int | None,
    ) -> DatasetUploadJobModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        if self.repo.get_project(org_id, project_id) is None:
            raise NotFoundError("project not found")
        safe = sanitize_filename(filename)
        if expected_size is not None:
            validate_size(expected_size, self.max_upload_bytes)
        job = DatasetUploadJobModel(
            organization_id=org_id,
            project_id=project_id,
            created_by_user_id=user_id,
            status=UploadJobStatus.PENDING.value,
            original_filename=safe,
            content_type=content_type,
            expected_size=expected_size,
            temp_storage_key=f"_uploads/{org_id}/{uuid7()}",
        )
        return self.repo.add_upload_job(job)

    def receive_multipart_part(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        job_id: uuid.UUID,
        part_number: int,
        stream: BinaryIO,
        size: int,
    ) -> DatasetUploadJobModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        job = self.repo.get_upload_job(org_id, job_id)
        if job is None or job.created_by_user_id != user_id:
            raise NotFoundError("upload job not found")
        if part_number < 1:
            raise ValidationError("invalid part number")
        if job.temp_storage_key is None:
            raise ValidationError("upload job misconfigured")
        new_total = job.received_bytes + size
        validate_size(max(new_total, 1), self.max_upload_bytes)
        part_key = f"{job.temp_storage_key}/part-{part_number:05d}"
        self.storage.upload_stream(
            self.bucket, part_key, stream, length=size, content_type="application/octet-stream"
        )
        job.status = UploadJobStatus.RECEIVING.value
        job.received_bytes = new_total
        job.parts_received += 1
        meta = dict(job.metadata_json or {})
        parts = list(meta.get("parts", []))
        parts.append({"n": part_number, "key": part_key, "size": size})
        meta["parts"] = parts
        job.metadata_json = meta
        job.updated_at = utcnow()
        return job

    def complete_multipart_upload(
        self, user_id: uuid.UUID, org_id: uuid.UUID, job_id: uuid.UUID, *, name: str | None = None
    ) -> DatasetModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        job = self.repo.get_upload_job(org_id, job_id)
        if job is None or job.created_by_user_id != user_id:
            raise NotFoundError("upload job not found")
        parts = sorted((job.metadata_json or {}).get("parts", []), key=lambda p: int(p["n"]))
        if not parts:
            raise ValidationError("no parts received")
        job.status = UploadJobStatus.VALIDATING.value
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=Path(job.original_filename).suffix)
        tmp_path = Path(tmp.name)
        try:
            with tmp:
                for part in parts:
                    data = self.storage.download(self.bucket, part["key"])
                    tmp.write(data)
            dataset = self._finalize_from_path(
                user_id=user_id,
                org_id=org_id,
                project_id=job.project_id,
                path=tmp_path,
                original_filename=job.original_filename,
                content_type=job.content_type,
                dataset_id=None,
                name=name,
                description="",
                tags=[],
                parent_dataset_id=None,
            )
            job.status = UploadJobStatus.COMPLETED.value
            job.dataset_id = dataset.id
            job.updated_at = utcnow()
            for part in parts:
                try:
                    self.storage.delete(self.bucket, part["key"])
                except Exception:  # noqa: BLE001
                    pass
            return dataset
        except Exception as exc:
            job.status = UploadJobStatus.FAILED.value
            job.error_message = str(exc)[:2000]
            raise
        finally:
            tmp_path.unlink(missing_ok=True)

    # ---------- dataset ops ----------
    def get_dataset(self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID) -> DatasetModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        dataset = self.repo.get_dataset(org_id, dataset_id)
        if dataset is None:
            raise NotFoundError("dataset not found")
        return dataset

    def delete_dataset(self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID) -> None:
        self._require(user_id, org_id, Permission.PROJECT_DELETE)
        dataset = self.get_dataset(user_id, org_id, dataset_id)
        dataset.status = DatasetStatus.DELETED.value
        dataset.deleted_at = utcnow()
        dataset.updated_at = utcnow()
        DATASET_DELETED.inc()
        logger.info(
            "DatasetDeleted",
            extra={"tenant_id": str(org_id), "dataset_id": str(dataset_id), "user_id": str(user_id)},
        )

    def archive_dataset(self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID) -> DatasetModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        dataset = self.get_dataset(user_id, org_id, dataset_id)
        dataset.status = DatasetStatus.ARCHIVED.value
        dataset.archived_at = utcnow()
        dataset.updated_at = utcnow()
        return dataset

    def restore_dataset(self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID) -> DatasetModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        dataset = self.get_dataset(user_id, org_id, dataset_id)
        if dataset.status not in {DatasetStatus.ARCHIVED.value, DatasetStatus.FAILED.value}:
            raise ConflictError("dataset is not archived/failed")
        dataset.status = DatasetStatus.READY.value
        dataset.archived_at = None
        dataset.updated_at = utcnow()
        return dataset

    def toggle_favorite(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID
    ) -> bool:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        self.get_dataset(user_id, org_id, dataset_id)
        existing = self.repo.get_favorite(org_id, dataset_id, user_id)
        if existing:
            self.repo.delete_favorite(existing)
            return False
        self.repo.add_favorite(
            DatasetFavoriteModel(organization_id=org_id, dataset_id=dataset_id, user_id=user_id)
        )
        return True

    def download(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        dataset_id: uuid.UUID,
        *,
        version: int | None = None,
        ip: str | None = None,
        request_id: str | None = None,
    ) -> tuple[str, DatasetVersionModel]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        dataset = self.get_dataset(user_id, org_id, dataset_id)
        if dataset.status in {DatasetStatus.DELETED.value}:
            raise NotFoundError("dataset not found")
        ver_no = version or dataset.current_version
        ver = self.repo.get_version(org_id, dataset_id, ver_no)
        if ver is None or ver.status != DatasetStatus.READY.value:
            raise NotFoundError("dataset version not ready")
        url = self.storage.presigned_url(
            self.bucket, ver.storage_key, expires=timedelta(hours=1)
        )
        dataset.download_count += 1
        self.repo.add_download_log(
            DatasetDownloadLogModel(
                organization_id=org_id,
                dataset_id=dataset_id,
                dataset_version_id=ver.id,
                user_id=user_id,
                ip_address=ip,
                request_id=request_id,
            )
        )
        DATASET_DOWNLOADED.inc()
        logger.info(
            "DatasetDownloaded",
            extra={"tenant_id": str(org_id), "dataset_id": str(dataset_id), "version": ver_no},
        )
        return url, ver

    def search(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        **kwargs: object,
    ) -> tuple[list[DatasetModel], int]:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        rows, total = self.repo.search_datasets(org_id, **kwargs)  # type: ignore[arg-type]
        return list(rows), total

    def create_connector(
        self,
        user_id: uuid.UUID,
        org_id: uuid.UUID,
        name: str,
        connector_type: str,
        project_id: uuid.UUID | None,
        config: dict[str, object],
    ) -> DatasetConnectorModel:
        self._require(user_id, org_id, Permission.PROJECT_WRITE)
        return self.repo.add_connector(
            DatasetConnectorModel(
                organization_id=org_id,
                project_id=project_id,
                name=name,
                connector_type=connector_type,
                config=config,
                created_by_user_id=user_id,
            )
        )

    def add_comment(
        self, user_id: uuid.UUID, org_id: uuid.UUID, dataset_id: uuid.UUID, body: str
    ) -> DatasetCommentModel:
        self._require(user_id, org_id, Permission.PROJECT_READ)
        self.get_dataset(user_id, org_id, dataset_id)
        return self.repo.add_comment(
            DatasetCommentModel(
                organization_id=org_id, dataset_id=dataset_id, user_id=user_id, body=body.strip()
            )
        )

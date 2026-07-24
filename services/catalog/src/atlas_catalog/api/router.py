"""Catalog HTTP routers — projects & datasets."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from atlas_identity.api.deps import CurrentUser, _client_ip, require_org_context
from fastapi import APIRouter, File, Form, Query, Request, UploadFile
from fastapi.responses import JSONResponse

from atlas_catalog.api.deps import CatalogSvc
from atlas_catalog.application.schemas import (
    CommentCreateRequest,
    CommentResponse,
    ConnectorCreateRequest,
    ConnectorResponse,
    DatasetListResponse,
    DatasetMetadataResponse,
    DatasetResponse,
    DatasetVersionResponse,
    DownloadResponse,
    ProjectCreateRequest,
    ProjectResponse,
    ProjectUpdateRequest,
    UploadJobResponse,
)
from atlas_catalog.infrastructure.models import DatasetModel

projects_router = APIRouter(prefix="/projects", tags=["projects"])
datasets_router = APIRouter(prefix="/datasets", tags=["datasets"])
connectors_router = APIRouter(prefix="/connectors", tags=["connectors"])


def _dataset_response(
    dataset: DatasetModel, *, tags: list[str] | None = None, is_favorite: bool = False
) -> DatasetResponse:
    return DatasetResponse(
        id=dataset.id,
        organization_id=dataset.organization_id,
        project_id=dataset.project_id,
        name=dataset.name,
        slug=dataset.slug,
        description=dataset.description,
        status=dataset.status,
        format=dataset.format,
        original_filename=dataset.original_filename,
        created_by_user_id=dataset.created_by_user_id,
        current_version=dataset.current_version,
        download_count=dataset.download_count,
        is_favorite=is_favorite,
        tags=tags or [],
        created_at=dataset.created_at,
        updated_at=dataset.updated_at,
    )


@projects_router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    body: ProjectCreateRequest, ctx: CurrentUser, svc: CatalogSvc
) -> ProjectResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    project = svc.create_project(
        ctx.user_id, ctx.organization_id, body.name, body.slug, body.description, body.tags
    )
    return ProjectResponse.model_validate(project)


@projects_router.get("", response_model=list[ProjectResponse])
def list_projects(
    ctx: CurrentUser, svc: CatalogSvc
) -> list[ProjectResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return [ProjectResponse.model_validate(p) for p in svc.list_projects(ctx.user_id, ctx.organization_id)]


@projects_router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> ProjectResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    return ProjectResponse.model_validate(
        svc.get_project(ctx.user_id, ctx.organization_id, project_id)
    )


@projects_router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    body: ProjectUpdateRequest,
    ctx: CurrentUser,
    svc: CatalogSvc,
) -> ProjectResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    project = svc.update_project(
        ctx.user_id,
        ctx.organization_id,
        project_id,
        name=body.name,
        description=body.description,
        tags=body.tags,
        is_archived=body.is_archived,
    )
    return ProjectResponse.model_validate(project)


@projects_router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> None:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.delete_project(ctx.user_id, ctx.organization_id, project_id)


@datasets_router.post("/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    request: Request,
    ctx: CurrentUser,
    svc: CatalogSvc,
    file: UploadFile = File(...),
    project_id: UUID = Form(...),
    dataset_id: UUID | None = Form(None),
    name: str | None = Form(None),
    description: str = Form(""),
    tags: str = Form(""),
) -> DatasetResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    tag_list = [t.strip() for t in tags.split(",") if t.strip()]
    size = request.headers.get("content-length")
    dataset = svc.upload_stream(
        user_id=ctx.user_id,
        org_id=ctx.organization_id,
        project_id=project_id,
        filename=file.filename or "upload.bin",
        stream=file.file,
        size=int(size) if size and size.isdigit() else None,
        content_type=file.content_type,
        dataset_id=dataset_id,
        name=name,
        description=description,
        tags=tag_list,
    )
    return _dataset_response(dataset, tags=tag_list)


@datasets_router.post("/upload/init", response_model=UploadJobResponse, status_code=201)
def init_upload(
    ctx: CurrentUser,
    svc: CatalogSvc,
    project_id: UUID = Form(...),
    filename: str = Form(...),
    content_type: str | None = Form(None),
    expected_size: int | None = Form(None),
) -> UploadJobResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    job = svc.init_multipart_upload(
        ctx.user_id, ctx.organization_id, project_id, filename, content_type, expected_size
    )
    return UploadJobResponse.model_validate(job)


@datasets_router.put("/upload/{job_id}/parts/{part_number}", response_model=UploadJobResponse)
async def upload_part(
    job_id: UUID,
    part_number: int,
    request: Request,
    ctx: CurrentUser,
    svc: CatalogSvc,
) -> UploadJobResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    body = await request.body()
    from io import BytesIO

    job = svc.receive_multipart_part(
        ctx.user_id,
        ctx.organization_id,
        job_id,
        part_number,
        BytesIO(body),
        len(body),
    )
    return UploadJobResponse.model_validate(job)


@datasets_router.post("/upload/{job_id}/complete", response_model=DatasetResponse)
def complete_upload(
    job_id: UUID,
    ctx: CurrentUser,
    svc: CatalogSvc,
    name: str | None = Form(None),
) -> DatasetResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    dataset = svc.complete_multipart_upload(ctx.user_id, ctx.organization_id, job_id, name=name)
    return _dataset_response(dataset)


@datasets_router.get("/search", response_model=DatasetListResponse)
def search_datasets(
    ctx: CurrentUser,
    svc: CatalogSvc,
    q: str | None = None,
    project_id: UUID | None = None,
    tag: str | None = None,
    owner: UUID | None = None,
    dataset_type: str | None = None,
    favorite: bool = False,
    uploaded_after: datetime | None = None,
    uploaded_before: datetime | None = None,
    sort: str = Query(
        "newest",
        pattern="^(newest|oldest|largest|smallest|most_downloaded|most_recent)$",
    ),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> DatasetListResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    rows, total = svc.search(
        ctx.user_id,
        ctx.organization_id,
        q=q,
        project_id=project_id,
        tag=tag,
        owner_id=owner,
        dataset_format=dataset_type,
        favorite_user_id=ctx.user_id if favorite else None,
        uploaded_after=uploaded_after,
        uploaded_before=uploaded_before,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    items = []
    for d in rows:
        tags = [t.tag for t in svc.repo.list_tags(d.id)]
        fav = svc.repo.get_favorite(ctx.organization_id, d.id, ctx.user_id) is not None
        items.append(_dataset_response(d, tags=tags, is_favorite=fav))
    return DatasetListResponse(items=items, total=total, limit=limit, offset=offset)


@datasets_router.get("", response_model=DatasetListResponse)
def list_datasets(
    ctx: CurrentUser,
    svc: CatalogSvc,
    project_id: UUID | None = None,
    sort: str = "newest",
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> DatasetListResponse:
    return search_datasets(
        ctx=ctx,
        svc=svc,
        q=None,
        project_id=project_id,
        tag=None,
        owner=None,
        dataset_type=None,
        favorite=False,
        uploaded_after=None,
        uploaded_before=None,
        sort=sort,
        limit=limit,
        offset=offset,
    )


@datasets_router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> DatasetResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    d = svc.get_dataset(ctx.user_id, ctx.organization_id, dataset_id)
    tags = [t.tag for t in svc.repo.list_tags(d.id)]
    fav = svc.repo.get_favorite(ctx.organization_id, d.id, ctx.user_id) is not None
    return _dataset_response(d, tags=tags, is_favorite=fav)


@datasets_router.get("/{dataset_id}/metadata", response_model=DatasetMetadataResponse)
def get_metadata(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> DatasetMetadataResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    d = svc.get_dataset(ctx.user_id, ctx.organization_id, dataset_id)
    tags = [t.tag for t in svc.repo.list_tags(d.id)]
    fav = svc.repo.get_favorite(ctx.organization_id, d.id, ctx.user_id) is not None
    current = None
    storage = None
    statistics = None
    if d.current_version:
        ver = svc.repo.get_version(ctx.organization_id, d.id, d.current_version)
        if ver is not None:
            current = DatasetVersionResponse.model_validate(ver)
            storage = {"bucket": svc.bucket, "object_key": ver.storage_key}
            statistics = {
                "row_estimate": ver.row_estimate,
                "column_estimate": ver.column_estimate,
                "size_bytes": ver.size_bytes,
            }
    return DatasetMetadataResponse(
        dataset=_dataset_response(d, tags=tags, is_favorite=fav),
        current=current,
        tags=tags,
        storage=storage,
        statistics=statistics,
    )


@datasets_router.get("/{dataset_id}/versions", response_model=list[DatasetVersionResponse])
def list_versions(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> list[DatasetVersionResponse]:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.get_dataset(ctx.user_id, ctx.organization_id, dataset_id)
    return [
        DatasetVersionResponse.model_validate(v)
        for v in svc.repo.list_versions(ctx.organization_id, dataset_id)
    ]


@datasets_router.post("/{dataset_id}/download", response_model=DownloadResponse)
def download_dataset(
    dataset_id: UUID,
    request: Request,
    ctx: CurrentUser,
    svc: CatalogSvc,
    version: int | None = None,
) -> DownloadResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    url, ver = svc.download(
        ctx.user_id,
        ctx.organization_id,
        dataset_id,
        version=version,
        ip=_client_ip(request),
        request_id=request.headers.get("x-request-id"),
    )
    return DownloadResponse(
        url=url,
        expires_in_seconds=3600,
        dataset_id=dataset_id,
        version=ver.version,
        filename=ver.original_filename,
    )


@datasets_router.post("/{dataset_id}/favorite")
def favorite_dataset(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> JSONResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    favored = svc.toggle_favorite(ctx.user_id, ctx.organization_id, dataset_id)
    return JSONResponse({"favorite": favored})


@datasets_router.post("/{dataset_id}/archive", response_model=DatasetResponse)
def archive_dataset(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> DatasetResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    d = svc.archive_dataset(ctx.user_id, ctx.organization_id, dataset_id)
    return _dataset_response(d)


@datasets_router.post("/{dataset_id}/restore", response_model=DatasetResponse)
def restore_dataset(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> DatasetResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    d = svc.restore_dataset(ctx.user_id, ctx.organization_id, dataset_id)
    return _dataset_response(d)


@datasets_router.delete("/{dataset_id}", status_code=204)
def delete_dataset(
    dataset_id: UUID, ctx: CurrentUser, svc: CatalogSvc
) -> None:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    svc.delete_dataset(ctx.user_id, ctx.organization_id, dataset_id)


@datasets_router.post("/{dataset_id}/comments", response_model=CommentResponse, status_code=201)
def add_comment(
    dataset_id: UUID,
    body: CommentCreateRequest,
    ctx: CurrentUser,
    svc: CatalogSvc,
) -> CommentResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.add_comment(ctx.user_id, ctx.organization_id, dataset_id, body.body)
    return CommentResponse.model_validate(row)


@connectors_router.post("", response_model=ConnectorResponse, status_code=201)
def create_connector(
    body: ConnectorCreateRequest, ctx: CurrentUser, svc: CatalogSvc
) -> ConnectorResponse:
    ctx = require_org_context(ctx)
    assert ctx.organization_id is not None
    row = svc.create_connector(
        ctx.user_id, ctx.organization_id, body.name, body.connector_type, body.project_id, body.config
    )
    return ConnectorResponse.model_validate(row)


def build_catalog_router() -> APIRouter:
    router = APIRouter()
    router.include_router(projects_router)
    router.include_router(datasets_router)
    router.include_router(connectors_router)
    return router

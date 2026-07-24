# Catalog Service

Bounded context for **projects**, **datasets**, **versions**, and **connectors**.

## Layout

```text
domain/           statuses, formats, validation
application/      use cases + schemas
infrastructure/   SQLAlchemy models, repository, estimates
api/              FastAPI routers
```

Mounted by `apps/api` under `/v1/projects`, `/v1/datasets`, `/v1/connectors`.

## Storage layout (MinIO)

```text
{tenant}/{project}/{dataset}/{version}/{uuid}{ext}
```

Files are never stored in PostgreSQL — only metadata.

## Statuses

`uploading` → `validating` → `ready` | `failed` → `archived` | `deleted`

## Formats

CSV, TSV, Excel (`.xlsx`), JSON, Parquet, ZIP (of supported members).

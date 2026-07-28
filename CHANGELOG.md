# Changelog

All notable changes to ATLAS are documented here.

## [0.7.0] — 2026-07-28 — ATLAS Training Engine

### Added

- `services/modeling` Clean Architecture package (deterministic training engine, adapters, metrics, artifacts, HITL approval)
- Training Agent (`agents/training` + `atlas_modeling.application.agent`)
- Algorithm adapter interface with Phase 7 baseline adapters (Logistic/Linear/Tree/Forest/ExtraTrees/KNN/NaiveBayes/SVM/XGBoost-if-installed/Dummy; LightGBM/CatBoost placeholders)
- Deterministic train/validation pipeline with seed, shuffle, stratify, and cross-validation placeholder flags
- Classification metrics (accuracy, precision, recall, f1, roc auc, confusion matrix, balanced accuracy)
- Regression metrics (mae, mse, rmse, r2, mape, residual statistics)
- MinIO training artifact persistence (`model.pkl`, `model.onnx` placeholder, report/metrics/pipeline/config/schema JSON)
- Async Celery jobs (`atlas.worker.training`) with queued/running/awaiting_approval/completed/failed/rejected flow
- Immutable model versions, training lineage, metrics, logs, and artifact references
- Alembic `0007_training_engine` (`modeling` schema, 10 tables)
- API under `/v1/training/*`
- Web pages `/training` and `/training/[id]`
- Unit tests for training engine metrics

### Changed

- Version **0.7.0** across workspace/API/worker/web
- API/worker/docker wiring now installs `atlas-modeling`

### Notes

- Phase 7 intentionally excludes HPO, experiment comparison, explainability, deployment, and monitoring

## [0.6.0] — 2026-07-27 — ATLAS Intelligent Feature Engineering Platform

### Added

- `services/feature_store` Clean Architecture package (generation engine, pipelines, HITL approval, offline store)
- Feature Engineering Agent (`agents/feature_engineering` + `atlas_feature_store.application.agent`)
- Feature generation: numeric interactions, polynomial/ratio/diff, log/sqrt/power, binning
- Time / text / categorical / numeric transforms; **encoding & scaling** (moved from Phase 5 deferral)
- Target-independent selection (variance threshold, correlation); target-dependent methods stubbed
- Offline feature store: registry, versions, views, lineage, tags, statistics, transformations
- HITL approve / reject / edit → immutable feature matrix as new catalog dataset version
- Async Celery jobs (`atlas.worker.features`) with awaiting_approval → approve/reject/export
- Approve creates a **new catalog dataset version** (never overwrites) + lineage `featured_from`
- Alembic `0006_feature_store` (`feature_store` schema, 10 tables)
- API under `/v1/features/*`
- Unit tests for the feature engineering engine

### Changed

- Version **0.6.0**; API/worker images install `atlas-feature-store`

### Notes

- Online feature serving is a **placeholder** (`online_enabled=False`; D022 offline-first in Phase 6)
- Target-dependent selection (target encoding, RFE, SHAP importance, etc.) deferred to **Phase 7**
- No training, HPO, or AutoML (Phase 7+)

## [0.5.0] — 2026-07-26 — ATLAS Intelligent Data Preparation Platform

### Added

- `services/preparation` Clean Architecture package (cleaning engine, recipes, HITL approval, versioned outputs)
- Data Cleaning Agent (`agents/data_cleaning` + `atlas_preparation.application.agent`)
- Missing-value strategies: mean, median, mode, constant, ffill, bfill, interpolate, KNN, iterative, drop rows/columns
- Duplicate handling: exact, near-duplicates, duplicate IDs
- Outlier detection: IQR, Z-score, modified Z, IsolationForest, LOF, DBSCAN with remove/cap/winsorize/leave
- Categorical/text/datetime/numeric hygiene transforms; executable JSON cleaning recipes
- Before/after quality comparison + transformation history
- Async Celery jobs (`atlas.worker.preparation`) with awaiting_approval → approve/reject
- Approve creates a **new catalog dataset version** (never overwrites) + lineage `cleaned_from`
- Alembic `0005_data_preparation` (`preparation` schema, 8 tables)
- API under `/v1/preparation/*`
- Web: preparation launcher + plan/recipe/before-after/timeline + HITL edit/approve/reject/export
- Unit + API integration tests for preparation

### Changed

- Version **0.5.0**; API/worker images install `atlas-preparation`

### Notes

- No feature engineering, training, HPO, or AutoML (Phase 6+)
- Encoding/scaling pipelines remain deferred to Feature Engineering (Phase 6) per AAEP sequencing

## [0.4.0] — 2026-07-24 — ATLAS Dataset Understanding Platform

### Added

- `services/profiling` Clean Architecture package (engine, quality, leakage, artifacts)
- First production agent: Dataset Understanding (`agents/dataset_understanding` + `atlas_profiling.application.agent`)
- Deterministic profiling: dtypes, missingness, duplicates, numeric/categorical/text/datetime stats
- Correlations (Pearson/Spearman/Kendall), outliers (IQR/Z/modified-Z/IsolationForest scores)
- Target & problem-type heuristics; data quality score (0–100) + health band
- Leakage heuristics (IDs, near-perfect predictors, future/timestamp names)
- Template NL summary with optional LLM provider port (stub by default)
- Reports: JSON, Markdown, HTML, PDF + Plotly visualization JSON stored in MinIO
- Async jobs via Celery (`atlas.worker.profiling`); inline execution in `testing` env
- Alembic `0004_dataset_profiling` (`profiling` schema, 7 tables)
- API under `/v1/profiling/*`
- Web: profiling launcher + dataset understanding report tabs
- Unit + API integration tests for profiling

### Changed

- Version **0.4.0**; worker image installs catalog/profiling stack
- Dockerfile.api installs `atlas-profiling`

### Fixed

- Ruff format compliance for CI (`ruff format --check apps packages tests`) so the python job passes

### Notes

- No cleaning, feature engineering, or training (Phase 5+)

## [0.3.0] — 2026-07-24 — ATLAS Dataset Ingestion Platform

### Added

- `services/catalog` Clean Architecture package (domain, application, infrastructure, API)
- Catalog project CRUD (source of truth for dataset ownership)
- Dataset upload (CSV, TSV, Excel, JSON, Parquet, ZIP) with streaming spool + MinIO storage
- Multipart upload jobs (init / parts / complete)
- Immutable dataset versions (v1, v2, …) under `tenant/project/dataset/version/uuid.ext`
- Metadata: checksum SHA-256, mime, encoding, size, row/column estimates, storage keys
- Validation: extension/MIME/size, empty files, path traversal, zip-bomb heuristics, magic sniff
- Search/filter/sort, favorites, archive/restore, soft-delete, signed download URLs
- Connector stubs (`sql` / `s3` / `stub`), comments, lineage, download logs, permissions, tags
- Alembic revision `0003_dataset_catalog` (`catalog` schema, 13 tables)
- Web: projects, project detail, dataset browser, drag-drop uploader with progress, dataset detail & versions
- Catalog unit + API integration tests; Prometheus counters for upload/download/delete
- `atlas_max_upload_bytes` setting (default 512 MiB); `ObjectStorage.upload_stream`
- UUIDv7 helpers in `atlas-core`

### Changed

- Version bumped to **0.3.0** across workspace / web / VERSION
- `/v1/projects` served by catalog (identity `projects` tables retained for legacy RBAC scaffolding)
- Dockerfile.api installs `atlas-catalog`

### Notes

- No profiling/EDA/agents (Phase 4+). `dataset_statistics` stores estimates only.

## [0.2.0] — 2026-07-24 — ATLAS Identity & Authentication

### Added

- `services/identity` Clean Architecture package (domain, application, infrastructure, API)
- JWT access + rotating refresh tokens, Argon2 password hashing, session revocation
- Organizations, memberships, invitations, organization switching
- RBAC roles: owner, admin, ml_engineer, data_scientist, approver, viewer
- Project-scoped membership foundation (no dataset features)
- API keys (create / list / rotate / revoke) with hashed storage and `X-API-Key` auth
- Audit log trail for auth and tenancy events
- OAuth/OIDC provider hook endpoint (stub / not_configured)
- Forgot/reset password architecture (mailer stubbed)
- Security headers middleware, login throttling via Redis
- Alembic revision `0002_identity_auth` (`identity` schema)
- Web: login, register, forgot password, protected shell, profile, API keys, members, org switcher
- Identity integration tests (`tests/test_identity.py`)

### Changed

- API version bumped to 0.2.0; Compose API image runs migrations on startup
- Dockerfile.api installs `atlas-identity`
- Root `VERSION` and `@atlas/web` set to `0.2.0`
- Added `py.typed` markers across workspace packages for mypy

## [0.1.1] — 2026-07-23 — Next.js production Docker fix

### Fixed

- Replaced nginx + `apps/web/out` static-export web image with a multi-stage Next.js production image (`output: "standalone"`, `node server.js`)
- Removed `output: "export"` so App Router can support future auth, API routes, sessions, and live updates
- Updated GitHub Actions Docker job to build the new web image successfully without a prebuilt `out/` directory
- Compose `web` service now runs the Next.js production server with wget healthchecks

### Changed

- `Dockerfile.web`: deps → builder → runner (pnpm, non-root `nextjs` user)
- Docs (README, ARCHITECTURE, ROADMAP, idea.md TD001) updated for production Next.js runtime

## [0.1.0] — 2026-07-23 — Phase 1 Platform Foundation

### Added

- uv Python workspace with packages: `atlas-core`, `atlas-contracts`, `atlas-db`, `atlas-storage`, `atlas-telemetry`, `atlas-ml`
- FastAPI application factory (`apps/api`) with config, DI container, middleware, exception handlers, health/live/ready/metrics
- Celery worker foundation (`apps/worker`) with Redis broker and heartbeat task
- Next.js App Router dashboard shell (`apps/web`) with sidebar navigation, theme switcher, and placeholder module pages
- SQLAlchemy 2.x + Alembic migration chain (empty foundation revision)
- MinIO object-storage port + adapter
- MLflow tracking URI abstraction (no experiment logging yet)
- Structured JSON logging, Prometheus metrics, OpenTelemetry tracing hook
- Docker multi-stage images for api/worker/web; binary-based minio/prometheus/grafana images
- Docker Compose stack: api, web, worker, postgres, redis, minio, mlflow, prometheus, grafana
- Helm chart + Kubernetes base manifests for the platform shell
- GitHub Actions CI (lint, typecheck, tests, image builds)
- Pre-commit hooks (ruff + basic hygiene)
- Smoke tests for config, API, worker, and shared packages
- `scripts/dev/fetch-binaries.ps1` for host-side MinIO/mc/Prometheus/Grafana Linux binaries
- `VERSION` file set to `0.1.0`

### Fixed (finalization)

- Prometheus `prometheus.yml` malformed `global` block (prevented scrape config load)
- Grafana image missing plugins/logs/provisioning directories
- Documented Docker Hub TLS workarounds and Python ≥3.11 constraint for slim base images

### Notes

- No datasets, training, agents, or Workflow Compiler in Phase 1 (deferred to later phases).

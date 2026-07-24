# Changelog

All notable changes to ATLAS are documented here.

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

# Changelog

All notable changes to ATLAS are documented here.

## [0.1.0] — 2026-07-23 — Phase 1 Platform Foundation

### Added

- uv Python workspace with packages: `atlas-core`, `atlas-contracts`, `atlas-db`, `atlas-storage`, `atlas-telemetry`, `atlas-ml`
- FastAPI application factory (`apps/api`) with config, DI container, middleware, exception handlers, health/live/ready/metrics
- Celery worker foundation (`apps/worker`) with Redis broker and heartbeat task
- Next.js App Router dashboard shell (`apps/web`) with sidebar navigation, theme switcher, and placeholder module pages
- Static export (`output: "export"`) served by nginx in Compose for reliable offline image builds
- SQLAlchemy 2.x + Alembic migration chain (empty foundation revision)
- MinIO object-storage port + adapter
- MLflow tracking URI abstraction (no experiment logging yet)
- Structured JSON logging, Prometheus metrics, OpenTelemetry tracing hook
- Docker multi-stage images for api/worker; nginx web image; binary-based minio/prometheus/grafana images
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
- Next.js nav hrefs missing trailing slashes under `trailingSlash: true` (static export client routing)
- Documented Docker Hub TLS workarounds and Python ≥3.11 constraint for slim base images

### Notes

- No authentication, datasets, training, agents, or Workflow Compiler in this release (deferred to later phases per `idea.md` / `ROADMAP.md`).
- GitHub Release for **“ATLAS Platform Foundation”** can be created from tag `v0.1.0` after push.

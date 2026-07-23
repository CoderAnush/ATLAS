# ATLAS

**A**utonomous **T**raining, **L**earning **A**nd **S**erving

> From Raw Data to Production AI with One Command.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-v0.1.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](./pyproject.toml)
[![Phase](https://img.shields.io/badge/phase-1%20frozen-brightgreen.svg)](./ROADMAP.md)
[![CI](https://img.shields.io/github/actions/workflow/status/CoderAnush/ATLAS/ci.yml?branch=main&label=CI)](https://github.com/CoderAnush/ATLAS/actions)

ATLAS is an enterprise-grade **Autonomous AI Engineering Platform (AAEP)**. Upload data, describe your goal in natural language, and receive a trained, explainable, deployable, monitored model—orchestrated by specialized AI agents.

| | |
|---|---|
| **Release** | **v0.1.0 — ATLAS Platform Foundation** |
| **Status** | Phase 1 frozen — permanent platform base |
| **License** | MIT |

Business features (auth, datasets, training, agents) start in **Phase 2+**. Do not implement them until the roadmap phase is explicitly approved.

---

## Technology stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Pydantic Settings, Uvicorn |
| Worker | Celery + Redis |
| Web | Next.js 15 (App Router), React 19, Tailwind CSS |
| Data | PostgreSQL 15, Redis 7, MinIO (S3) |
| ML ops shell | MLflow tracking URI (no experiments yet) |
| Observability | Structured JSON logs, Prometheus, Grafana, OpenTelemetry hook |
| Python tooling | `uv`, Ruff, mypy, pytest |
| Frontend tooling | TypeScript, ESLint, Prettier |
| Containers | Docker Compose; Helm/K8s manifests (shell) |

---

## Prerequisites

| Tool | Notes |
|------|--------|
| Docker Desktop (or compatible engine) | Required for the full stack |
| `uv` | Python workspace (3.11+; 3.12 preferred) |
| Node.js 22 LTS | For local web development |
| `pnpm` (optional) | Preferred; `npm` works if Corepack/`pnpm` is blocked |
| Make (optional) | Convenience targets in `Makefile` |

On hosts with flaky Docker Hub TLS, pre-fetch Linux binaries once:

```powershell
pwsh scripts/dev/fetch-binaries.ps1
```

Then build the Next.js static export before Compose web image builds:

```bash
cd apps/web && npm install && npm run build && cd ../..
```

---

## Quick start (Docker)

```bash
# From the repository root
cp .env.example .env
# Recommended on Windows / first build:
#   pwsh scripts/dev/fetch-binaries.ps1
#   cd apps/web && npm install && npm run build && cd ../..
docker compose up --build -d
docker compose ps
```

Or: `make compose-up` (builds the web export, then Compose).

Once healthy:

| Service | URL |
|---------|-----|
| Web dashboard | http://localhost:3000 |
| API docs (OpenAPI) | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| API live / ready | http://localhost:8000/health/live · `/health/ready` |
| Metrics | http://localhost:8000/metrics |
| MLflow | http://localhost:5000 |
| MinIO API / console | http://localhost:9000 · http://localhost:9001 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (`admin` / `admin`) |

Stop:

```bash
docker compose down
```

Dev credentials in Compose (local only): Postgres `atlas`/`atlas`, MinIO `minioadmin`/`minioadmin`, Grafana `admin`/`admin`. Change before any shared or production use.

---

## Architecture (Phase 1)

```text
browser → web:3000 (nginx + Next.js static export)
       → api:8000  → postgres / redis / minio / mlflow
worker ← redis (Celery)
prometheus → api:/metrics
grafana → prometheus
```

Full design: [`ARCHITECTURE.md`](./ARCHITECTURE.md). Locked decisions: [`idea.md`](./idea.md).

---

## Project structure

```text
apps/
  api/            FastAPI composition root
  web/            Next.js App Router shell (static export for Compose)
  worker/         Celery worker
packages/         Shared Python libraries (core, contracts, db, storage, telemetry, ml)
                  + atlas-ui placeholder for shared frontend components
services/         Bounded contexts (business logic in later phases)
agents/           AI agent stubs (later phases)
infrastructure/
  docker/         Dockerfiles + host-fetched binaries (gitignored)
  monitoring/     Prometheus + Grafana provisioning
  helm/           Helm chart shell
  kubernetes/           Base manifests
tests/            Cross-cutting smoke tests
scripts/dev/      Helper scripts (e.g. fetch-binaries)
```

---

## Local development (without full Compose)

### Python / API

```bash
uv sync
cp .env.example .env
# Start postgres/redis/minio (or full compose infra) as needed
uv run uvicorn atlas_api.main:app --app-dir apps/api/src --reload --host 0.0.0.0 --port 8000
```

Quality gates:

```bash
uv run pytest
uv run ruff check apps packages tests
uv run mypy
# or: make release-check
```

### Web

```bash
cd apps/web
npm install   # or: pnpm install
npm run dev   # http://localhost:3000
npm run lint
npm run typecheck
```

### Worker

```bash
uv run celery -A atlas_worker.celery_app worker --loglevel=INFO
```

---

## Docker usage notes

- **API / worker** images install from exported `requirements-*.txt` (no `uv` inside the image).
- **Web** image serves `apps/web/out/` via nginx — run `npm run build` in `apps/web` before `docker compose build web`.
- **MinIO / Prometheus / Grafana** images unpack host-fetched Linux binaries from `infrastructure/docker/bin/` (see `scripts/dev/fetch-binaries.ps1`).
- **MLflow** image `pip install`s MLflow (first build is slow).
- Multi-stage builds are used for api/worker; web is a thin nginx stage.

Images built by Compose: `atlas-api`, `atlas-web`, `atlas-worker`, `atlas-minio`, `atlas-minio-init`, `atlas-mlflow`, `atlas-prometheus`, `atlas-grafana`.

---

## Screenshots

| Surface | Placeholder |
|---------|-------------|
| Dashboard shell | ![Dashboard](docs/screenshots/dashboard.png) — add after first UI polish |
| API `/docs` | ![OpenAPI](docs/screenshots/api-docs.png) — add screenshot of Swagger UI |
| Grafana | ![Grafana](docs/screenshots/grafana.png) — optional |

Create `docs/screenshots/` and drop PNGs when ready; links above are intentional placeholders for v0.1.0 docs.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `docker compose build` fails pulling Hub images (TLS / `HTTP response to HTTPS client`) | Prefer cached tags (`python:3.11-slim`, `postgres:15-alpine`, `redis:7-alpine`, `nginx:stable-alpine`). Run `pwsh scripts/dev/fetch-binaries.ps1` for MinIO/Prometheus/Grafana. |
| `web` build: missing files under `/usr/share/nginx/html` | Build the Next.js export first: `cd apps/web && npm run build`. |
| Prometheus unhealthy / YAML parse errors | Ensure `infrastructure/monitoring/prometheus/prometheus.yml` uses a nested `global:` block. |
| Grafana provisioning directory warnings | Empty `provisioning/plugins` and `provisioning/alerting` dirs are included; rebuild grafana image if upgrading. |
| Host `pnpm` / Corepack `EPERM` | Use `npm` locally; CI uses `pnpm/action-setup`. |
| `/health/ready` degraded | Check postgres, redis, minio, mlflow containers; see `docker compose logs api`. |
| Port already in use | Stop conflicting local Postgres/Redis or change Compose port mappings. |

---

## Roadmap

See [`ROADMAP.md`](./ROADMAP.md). Phase 1 (platform foundation) is **frozen** at v0.1.0. Phase 2 begins only with explicit approval.

---

## Contributing

See [`CONTRIBUTING.md`](./CONTRIBUTING.md). Short version:

1. Read [`idea.md`](./idea.md) first.  
2. Branch from `main` with Conventional Commits.  
3. Keep PRs focused; update docs when design changes.  
4. Never commit secrets (`.env` is gitignored).  

---

## Documentation map

| Document | Purpose |
|----------|---------|
| [`idea.md`](./idea.md) | **Single source of truth** |
| [`ARCHITECTURE.md`](./ARCHITECTURE.md) | System design |
| [`ROADMAP.md`](./ROADMAP.md) | Phased delivery |
| [`CHANGELOG.md`](./CHANGELOG.md) | Release notes |
| [`CONTRIBUTING.md`](./CONTRIBUTING.md) | Contribution guide |
| [`LICENSE`](./LICENSE) | MIT |

---

## Version

**v0.1.0 — ATLAS Platform Foundation**

Tagged on `main`. Create a GitHub Release from the tag when ready (title: *ATLAS Platform Foundation*).

---

## License

MIT © ATLAS Contributors

# ATLAS

**A**utonomous **T**raining, **L**earning **A**nd **S**erving

> From Raw Data to Production AI with One Command.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![Version](https://img.shields.io/badge/version-v0.6.0-blue.svg)](./CHANGELOG.md)
[![Python](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)](./pyproject.toml)
[![Phase](https://img.shields.io/badge/phase-6%20features-brightgreen.svg)](./ROADMAP.md)
[![CI](https://img.shields.io/github/actions/workflow/status/CoderAnush/ATLAS/ci.yml?branch=main&label=CI)](https://github.com/CoderAnush/ATLAS/actions)

ATLAS is an enterprise-grade **Autonomous AI Engineering Platform (AAEP)**. Upload data, describe your goal in natural language, and receive a trained, explainable, deployable, monitored model—orchestrated by specialized AI agents.

| | |
|---|---|
| **Release** | **v0.6.0 — ATLAS Intelligent Feature Engineering Platform** |
| **Status** | Phase 6 complete — feature pipelines, HITL approve, versioned feature matrices (offline store) |
| **License** | MIT |

Phase 6 (feature engineering) is complete. Training and later features start only with explicit Phase 7+ approval.

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

The **web** image builds Next.js inside Docker (multi-stage, `pnpm build` → standalone `node server.js`). No host `out/` directory is required.

---

## Authentication (Phase 2)

```bash
# Register (creates org + owner membership)
curl -X POST http://localhost:8000/v1/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"Str0ng!Pass","full_name":"You","organization_name":"Acme"}'

# Login
curl -X POST http://localhost:8000/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"you@example.com","password":"Str0ng!Pass"}'
```

Web UI: http://localhost:3000/login · `/register` · authenticated dashboard after sign-in.

OpenAPI: http://localhost:8000/docs

## Datasets (Phase 3)

```bash
# Create a project
curl -X POST http://localhost:8000/v1/projects \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"name":"Demo","description":"First project"}'

# Upload a CSV
curl -X POST http://localhost:8000/v1/datasets/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F project_id=$PROJECT_ID -F file=@./data.csv
```

UI: http://localhost:3000/projects · `/datasets` · `/datasets/upload`

## Profiling (Phase 4)

```bash
# Start async profiling job
curl -X POST http://localhost:8000/v1/profiling/run/$DATASET_ID \
  -H "Authorization: Bearer $TOKEN"

# Read summary
curl http://localhost:8000/v1/profiling/$DATASET_ID/summary \
  -H "Authorization: Bearer $TOKEN"
```

UI: http://localhost:3000/profiling

## Preparation (Phase 5)

```bash
# Start cleaning analysis (HITL — does not mutate source)
curl -X POST http://localhost:8000/v1/preparation/run/$DATASET_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"strategies":{}}'

# Approve → creates new dataset version
curl -X POST http://localhost:8000/v1/preparation/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}"
```

UI: http://localhost:3000/preparation

## Features (Phase 6)

```bash
# Start feature engineering analysis (HITL — does not mutate source)
curl -X POST http://localhost:8000/v1/features/run/$DATASET_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"config":{}}'

# Approve → creates new dataset version with feature matrix
curl -X POST http://localhost:8000/v1/features/approve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"job_id\":\"$JOB_ID\"}"
```

API: `/v1/features/*` · Online feature serving is a placeholder (offline-first).

After upgrading, ensure migrations run (API container runs `alembic upgrade head` on start):

```bash
docker compose up --build -d api
# or locally (with Postgres reachable):
# cd apps/api && uv run python run_migrations.py
```

```bash
# From the repository root
cp .env.example .env
# Recommended on Windows / first build:
#   pwsh scripts/dev/fetch-binaries.ps1
docker compose up --build -d
docker compose ps
```

Or: `make compose-up`.

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
browser → web:3000 (Next.js production server)
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
  web/            Next.js App Router shell (production Node server in Compose)
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
- **Web** image is a multi-stage Next.js build (`pnpm install` → `pnpm build` → standalone `node server.js`). No nginx; no `apps/web/out`.
- **MinIO / Prometheus / Grafana** images unpack host-fetched Linux binaries from `infrastructure/docker/bin/` (see `scripts/dev/fetch-binaries.ps1`).
- **MLflow** image `pip install`s MLflow (first build is slow).

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
| `web` image fails to build | Ensure Docker can pull `node:22-alpine`. The image builds Next.js inside the Dockerfile — no host `out/` directory is needed. |
| Host `pnpm` / Corepack `EPERM` | Use `npm` locally; Docker/CI use `pnpm`. |
| `/health/ready` degraded | Check postgres, redis, minio, mlflow containers; see `docker compose logs api`. |
| Port already in use | Stop conflicting local Postgres/Redis or change Compose port mappings. |

---

## Roadmap

See [`ROADMAP.md`](./ROADMAP.md). Phases 1–6 complete through **v0.6.0**. Do not start Phase 7 until explicitly approved.

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

**v0.6.0 — ATLAS Intelligent Feature Engineering Platform**

Ready to tag on `main` when approved. Create a GitHub Release from the tag (title: *ATLAS Intelligent Feature Engineering Platform*).

---

## License

MIT © ATLAS Contributors

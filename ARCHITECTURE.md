# ATLAS Architecture

High-level system design. For locked decisions, modules, and contracts, see **[`idea.md`](./idea.md)** (source of truth).

**Last Updated:** 2026-07-28 (Phase 9 experiment tracking)

ATLAS is an **Autonomous AI Engineering Platform (AAEP)**. Full specification: [`idea.md`](./idea.md) §30–§52. This file remains a concise topology guide; **`idea.md` wins on conflicts**.

### Phase 9 runtime topology

```text
browser → web:3000 (/experiments)
       → api:8000 /v1/experiments/*
training/HPO workers → auto-publish runs → experiments service
       → ExperimentTracker (MLflow adapter) + postgres experiments.*
postgres: identity.* · catalog.* · profiling.* · preparation.* · feature_store.* · modeling.* · hpo.* · experiments.*
```

**Experiment tracking:** MLflow behind `ExperimentTracker` port; auto-record from training/HPO; no explainability or deployment in Phase 9.

### Phase 8 runtime topology

```text
browser → web:3000 (/hpo)
       → api:8000 /v1/hpo/*
            → enqueue Celery job (atlas.worker.hpo)
worker → read approved training job + approved feature matrix → HPO Agent
       → persist hpo.* job/study/trials/artifacts (awaiting_approval)
human  → approve/reject best trial study
postgres: identity.* · catalog.* · profiling.* · preparation.* · feature_store.* · modeling.* · hpo.*
```

**HPO:** deterministic search where possible, Optuna-first, MinIO-backed artifacts, no deployment or experiment comparison in Phase 8.

**Runtime smoke (v0.8.0):** Compose stack verified through features → training → HPO approve. Feature matrices retain the supervised target; training dedupes/coerces encoded columns; HPO deps bind `container.storage`.

### Phase 7 runtime topology

```text
browser → web:3000 (/training)
       → api:8000 /v1/training/*
            → enqueue Celery job (atlas.worker.training)
worker → read approved feature matrix + profiling metadata → Training Agent
       → persist modeling.* job/model/metrics/artifacts/lineage (awaiting_approval)
human  → approve/reject model registration
postgres: identity.* · catalog.* · profiling.* · preparation.* · feature_store.* · modeling.*
```

**Training:** deterministic execution with immutable lineage/artifacts; no deployment in Phase 7.

### Phase 6 runtime topology

```text
browser → web:3000 (/features)
       → api:8000 /v1/features/*
            → enqueue Celery job (atlas.worker.features)
worker → download dataset + optional profile → Feature Engineering Agent
       → persist feature_store.* pipeline/report (awaiting_approval)
human  → approve/reject (+ optional edited steps)
       → on approve: materialize feature matrix → new catalog dataset version + lineage featured_from
postgres: identity.* · catalog.* · profiling.* · preparation.* · feature_store.*
```

**Feature engineering:** never mutates the source version; HITL gate before writing feature matrices.  
**Offline store:** registry, versions, views, lineage, tags, statistics; online serving placeholder (`online_enabled=False`).

### Phase 5 runtime topology

```text
browser → web:3000 (/preparation)
       → api:8000 /v1/preparation/*
            → enqueue Celery job (atlas.worker.preparation)
worker → download dataset + optional profile → Data Cleaning Agent
       → persist preparation.* plan/recipe/report (awaiting_approval)
human  → approve/reject (+ optional edited steps)
       → on approve: apply recipe → new catalog dataset version + lineage cleaned_from
postgres: identity.* · catalog.* · profiling.* · preparation.*
```

**Preparation:** never mutates the source version; HITL gate before writing cleaned artifacts.  
**Recipes:** versioned JSON step lists, replayable via `apply_recipe`.

### Phase 4 runtime topology

```text
browser → web:3000 (/profiling)
       → api:8000 /v1/profiling/*
            → enqueue Celery job
worker → download dataset from MinIO → Dataset Understanding Agent
       → persist profiling.* + artifacts to MinIO
postgres: identity.* · catalog.* · profiling.*
```

**Profiling:** deterministic EDA first; LLM summarization optional via provider port.  
**Artifacts:** JSON / Markdown / HTML / PDF / Plotly JSON under tenant-scoped MinIO keys.

---

## 1. Architectural Style

**Modular monolith** with strict bounded contexts, designed for **strangler-fig extraction** into microservices.

```text
┌──────────────────────────────────────────┐
│                 apps/web                 │
└────────────────────┬─────────────────────┘
                     │
┌────────────────────▼─────────────────────┐
│                 apps/api                 │  ← composition root
│         (routers + middleware DI)        │
└─────────┬─────────────────────┬──────────┘
          │                     │
          ▼                     ▼
   services/* (sync)     apps/worker (async)
          │                     │
          └──────────┬──────────┘
                     ▼
         packages/* + agents/*
                     │
          PostgreSQL · Redis · MinIO · MLflow
```

### Why this shape?

| Concern | Approach |
|---------|----------|
| Speed of early delivery | Single deployable API |
| Future scale | Context boundaries + no cross-schema joins |
| ML workloads | Workers/GPU pools independent of API pods |
| Extensibility | Plugins + agent contracts |
| Ops | Docker Compose → Helm/K8s without redesign |

### AAEP Five-Layer Overlay

Logical layers (do not replace bounded contexts):

```text
Experience → Intelligence → Execution → Infrastructure
                              ↑
                         Governance (cross-cutting)
```

| Layer | Responsibility | Details in idea.md |
|-------|----------------|--------------------|
| Experience | Web, REST, GraphQL, CLI, SDKs, IDE/Jupyter, mobile | §31.1 |
| Intelligence | Agents, Compiler, Graph, Memory, Meta Learning, Decisions | §31.2, §32–§36 |
| Execution | Pipelines, data, features, train, HPO, deploy, monitor | §31.3, §37–§40 |
| Infrastructure | K8s, Docker, PG, Redis, Kafka, MLflow, MinIO, Ray, OTel | §31.4 |
| Governance | RBAC, audit, RAI, cost/carbon, registry, HITL | §31.5, §44–§45 |

**Rule:** Natural language is compiled by the Workflow Compiler (`idea.md` §32); Intelligence proposes, Execution performs, Governance constrains.

---

## 2. Bounded Contexts

| Context | Owns | Future Service |
|---------|------|----------------|
| identity | Users, tenants, RBAC, API keys | auth-service |
| catalog | Projects, datasets, connectors | data-service |
| profiling | EDA, quality, leakage signals | (often stays with catalog) |
| preparation | Clean + feature recipes | feature-service |
| modeling | Train, HPO, adapters | training-service |
| evaluation | Metrics, leaderboards | (with modeling early) |
| explainability | SHAP/LIME/fairness artifacts | xai-service |
| registry | Model versions & stages | registry-service |
| serving | Deployments & traffic | inference-gateway |
| observability | Drift, alerts, live metrics | monitor-service |
| orchestration | Plans, DAGs, HITL | orchestrator-service |
| documentation | Model cards & reports | docs-service |
| cost | Estimates & recommendations | (library or small service) |
| plugins_host | Discovery & sandbox | plugin-service |

**Rule:** Depend on another context only through its **application API** or **published events**, never through internal repositories.

---

## 3. Clean Architecture Mapping

```text
adapters (FastAPI, Celery, SQLAlchemy, MinIO, MLflow)
        ↓
application (use cases / workflows)
        ↓
domain (entities, value objects, domain services)
        ↑
ports (interfaces) ← infrastructure implements
```

Shared kernel: `packages/atlas-core`, `packages/atlas-contracts`.

---

## 4. Agent Control Plane

Agents are **application services with LLM/tooling**, not free-form chat bots.

```text
User NL / UI action
      ↓
Orchestrator Agent  →  Workflow DAG + constraints + budgets
      ↓
Stage Agents (profile, clean, features, select, HPO, train, eval, xai, deploy, …)
      ↓
Artifacts + metrics + messages  →  Experiment tracker / object store
      ↓
HITL gate (approve / reject / canary / schedule)
      ↓
Serving + Monitoring (+ Retraining loop)
```

### Contracts

All agent I/O validated by Pydantic models in `packages/atlas-contracts`.

- Deterministic tools preferred for data transforms  
- LLMs for planning, summarization, recommendations  
- Every agent call audited with `run_id`  

---

## 5. Data Plane

| Store | Role |
|-------|------|
| PostgreSQL | System of record (metadata, authz, workflow state) |
| Redis | Cache, locks, Celery broker/backend (initial) |
| MinIO | Datasets, models, reports, images |
| MLflow | Experiment & registry backend (behind port) |
| Kafka/Redpanda | Later: high-volume domain events |

Logical DB schemas mirror contexts (`identity`, `catalog`, `modeling`, …).

---

## 6. API Design

- REST + OpenAPI 3 via FastAPI  
- Version prefix `/v1`  
- Problem+JSON style errors  
- Idempotency keys on create/run endpoints  
- Async operations return `202` + `job_id` / `run_id`  
- SSE/WebSocket for run progress (Phase 1+)  

---

## 7. Frontend Architecture

- Next.js App Router, TypeScript, `pnpm`  
- Server components for shell; client for interactive pipeline/chat  
- TanStack Query for server state  
- Design tokens via CSS variables (see UI principles in `idea.md`)  
- Route groups roughly match product areas: projects, data, experiments, models, deploy, monitor, admin  

---

## 8. Deployment Topology

### Local

Docker Compose: `web`, `api`, `worker`, `postgres`, `redis`, `minio`, `mlflow`, (optional `prometheus`/`grafana`).

### Kubernetes

```text
Ingress → web + api
       → worker Deployment (CPU) + GPU worker pool (later)
       → postgres / redis / minio (or managed equivalents)
Helm chart: infrastructure/helm/atlas
```

### Progressive Delivery

`None → Staging → Canary → Production` with automated rollback on SLO breach.

---

## 9. Observability

- **Logs:** structured JSON, `request_id`, `tenant_id`, `run_id`  
- **Metrics:** RED for API; training job metrics; inference latency/error  
- **Traces:** OpenTelemetry across api → worker → external deps  
- **Audit:** security-sensitive mutations immutable  

---

## 10. Security Architecture

```text
Client → TLS → API Gateway middleware
              → AuthN (JWT/OAuth/API key)
              → AuthZ (RBAC + tenant scoping)
              → Rate limit
              → Handler
```

Secrets via environment / K8s Secrets / vault later. Plugins isolated progressively (process → container).

### 10.1 Authentication flow (Phase 2)

```text
Register/Login
   → Argon2 verify / hash
   → create Session + RefreshToken (hashed)
   → issue JWT access (short-lived) + refresh (opaque, rotating)
   → audit: login | register

Access request
   → Bearer JWT  OR  X-API-Key (hashed lookup)
   → principal: user_id, org_id, role, session_id
   → tenant middleware binds organization context

Refresh
   → validate refresh hash, revoke old, mint new pair (rotation)
   → revoked / expired → 401

Logout
   → revoke session (+ refresh tokens) → audit
```

Forgot/reset password and email verification are wired as architecture with a **stubbed mailer** (tokens stored hashed; no SMTP in Phase 2).

### 10.2 Authorization & RBAC

| Role | Typical powers |
|------|----------------|
| owner | Billing, delete org, all admin |
| admin | Members, settings, API keys, projects |
| ml_engineer | Train/deploy scoped project ops (later phases) |
| data_scientist | Experiment / data scoped ops (later phases) |
| approver | HITL gates (later phases) |
| viewer | Read-only |

Hierarchy: `owner > admin > ml_engineer > data_scientist > approver > viewer`.  
Endpoint guards call `require_permission(...)`; project membership can further narrow access.

### 10.3 Multi-tenancy

- Every authenticated principal carries `organization_id` (active org).
- Repositories filter by `organization_id`; handlers must not query across tenants.
- Switching org updates `users.active_organization_id` and is audited.
- Projects belong to exactly one organization.

### 10.4 Identity schema (`identity`)

Tables: `users`, `organizations`, `memberships`, `projects`, `project_memberships`, `sessions`, `refresh_tokens`, `api_keys`, `audit_logs`.  
Migration: `apps/api/alembic/versions/0002_identity_auth.py`.

```text
organizations 1──* memberships *──1 users
organizations 1──* projects 1──* project_memberships
users 1──* sessions / refresh_tokens / api_keys
* ──▶ audit_logs (append-only)
```

---

## 11. Plugin Architecture

```text
plugins/<type>/<name>/
  plugin.toml | pyproject entry point
  atlas_plugin.py  # implements port interfaces
```

Host loads manifests, validates permissions, registers hooks (connectors, algorithms, metrics, notifications, agents).

---

## 12. Failure & Resilience

- Workers: retries with jitter; dead-letter for poison jobs  
- Training: checkpoint when framework allows; budget timeouts  
- Deploy: health checks + ready gates; rollback revision  
- Orchestrator: durable workflow state; resume after crash  

---

## 13. Scalability Model

| Tier | Strategy |
|------|----------|
| API | Horizontal pods, stateless |
| Workers | Queue depth autoscaling; GPU node pools |
| DB | Read replicas later; partition large logs |
| Objects | S3-compatible; CDN optional for UI assets |
| Agents | Cap concurrency per tenant; token/cost budgets |

Target design point: **thousands of concurrent users**, bursty training workloads, multi-tenant isolation.

---

## 14. Evolution Checklist (Extract a Service)

1. No cross-context SQL joins  
2. Own Alembic migrations / schema  
3. Own Docker image & Helm subchart  
4. Sync API replaced with HTTP/gRPC + events  
5. Independent SLO and on-call  

---

## 15. Related Docs

- [`idea.md`](./idea.md) — decisions, agents, schema overview, stack  
- [`ROADMAP.md`](./ROADMAP.md) — phased delivery  
- [`CONTRIBUTING.md`](./CONTRIBUTING.md) — engineering standards  

---

*Update this file when topology, context boundaries, or deployment model change—and mirror critical decisions into `idea.md`.*

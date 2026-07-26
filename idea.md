# ATLAS — Single Source of Truth

> **A**utonomous **T**raining, **L**earning **A**nd **S**erving  
> *From Raw Data to Production AI with One Command.*

**Internal product identity:** **ATLAS — Autonomous AI Engineering Platform (AAEP)**  
**Status:** Phase 5 complete — **v0.5.0 Intelligent Data Preparation Platform**; awaiting Phase 6 instructions  
**Last Updated:** 2026-07-26  
**Primary Branch:** `main`  
**License:** MIT  
**Repository:** https://github.com/CoderAnush/ATLAS  
**Package Managers:** `uv` (Python), `pnpm`/`npm` (frontend)  
**Runtime:** `docker compose up --build` brings up api, web, worker, postgres, redis, minio, mlflow, prometheus, grafana  

---

## Document Maintenance Rules

1. This file is the **single source of truth**. Read it before any engineering work.  
2. **Never delete** locked design decisions, roadmap phases, modules, or agents without an explicit superseding decision recorded here.  
3. New capability is added by **extension** (new sections, new decision IDs, additive roadmap rows).  
4. Cross-reference related sections (e.g., Workflow Compiler ↔ Intelligence Layer ↔ Orchestration).  
5. Mirror critical topology changes into `ARCHITECTURE.md` and delivery phasing into `ROADMAP.md`.  

---

## 1. Vision

ATLAS is an enterprise-grade **AI Operating System for Machine Learning**. It is not an AutoML clone. It is an agent-driven platform that automates the full ML lifecycle—from raw data to production inference, monitoring, and continuous improvement—with minimal human intervention while remaining transparent, auditable, and controllable.

Target quality bar: Vertex AI, SageMaker, Azure ML, Databricks, DataRobot, Kubeflow, MLflow, H2O.ai—augmented with an LLM-powered multi-agent control plane.

Internally, ATLAS is defined as an **Autonomous AI Engineering Platform (AAEP)**—an intelligent system capable of planning, building, deploying, monitoring, improving, and governing AI systems with human oversight. See §30.

---

## 2. Mission

Enable any user to:

1. Upload or connect a dataset  
2. Describe a goal in natural language  
3. Receive a trained, optimized, explainable, deployable, monitored, production-ready model  

…without requiring deep ML expertise, while giving experts full control when they need it.

Extended AAEP mission: convert natural-language intent into **validated, optimized, observable execution graphs**; learn from organizational history via a Knowledge Graph and Meta Learning; and continuously improve recommendations under Governance and Responsible AI constraints.

---

## 3. Goals

| Priority | Goal |
|----------|------|
| P0 | End-to-end tabular classification/regression pipeline (ingest → train → evaluate → register) |
| P0 | Multi-agent orchestration with structured inter-agent contracts |
| P0 | Experiment tracking + model registry |
| P1 | Explainability, deployment (FastAPI + Docker + K8s), monitoring |
| P1 | Natural-language workflow compilation |
| P2 | Plugin ecosystem, feature store, cost optimization |
| P2 | NLP / CV / time-series / multimodal |
| P2 | Five-layer AAEP architecture realization (Experience → Intelligence → Execution → Infrastructure → Governance) |
| P2 | Knowledge Graph, Agent Memory, Meta Learning, Resource Scheduler foundations |
| P3 | Federated learning, synthetic data, enterprise multi-tenancy at scale |
| P3 | RAG Builder, Prompt Studio, LLM Evaluation, Research Mode, Marketplaces |
| P3 | Visual Workflow Builder, Live Collaboration, Chaos Engineering, SDK Generator |
| P3 | Product lines: ATLAS Cloud, Edge, Research, Enterprise editions |

### Non-Goals (Near Term)

- Replacing every cloud AutoML UI feature on day one  
- Training foundation models from scratch as a core product  
- Guaranteeing best-in-world accuracy without human review for regulated use cases  
- Shipping every AAEP module in v1.0 (see §51 Enterprise Roadmap for staged delivery)  

---

## 4. Core Philosophy

- **Agent-driven:** Every ML lifecycle stage is owned by a specialized agent.  
- **Human-in-the-loop:** Production deployment requires explicit approval gates.  
- **Modular monolith first:** One deployable API today; clear bounded contexts for microservice extraction later.  
- **Contract-first:** Agents, APIs, and plugins communicate via versioned schemas.  
- **Observable by default:** Traces, metrics, logs, audit events for every run.  
- **Reproducible:** Datasets, code, env, seeds, and artifacts are always recorded.  
- **Compile, don’t improvise:** Natural language is compiled to DAGs via the Workflow Compiler (§32)—never executed as raw unconstrained prompts against production systems.  
- **Learn from history:** Meta Learning and the Knowledge Graph bias plans toward what worked before (§33–§35).  
- **Governed autonomy:** Intelligence is bounded by Governance Layer controls (RBAC, audit, RAI, cost, carbon) (§31.5).  

---

## 5. Design Decisions (Locked)

| ID | Decision | Rationale |
|----|----------|-----------|
| D001 | Git monorepo (repository root) | Single versioning, shared contracts, atomic cross-cutting changes |
| D002 | Modular monolith → microservices-ready | Speed of delivery now; extract services along bounded contexts later |
| D003 | Python ≥3.11 via `uv` (3.12+ preferred locally) + Node LTS (`pnpm` preferred; `npm` acceptable) | Modern tooling; Docker images use 3.11-slim for broader base-image availability |
| D004 | FastAPI for API surface | Async, OpenAPI-native, production proven |
| D005 | PostgreSQL as system of record | Strong consistency for users, projects, runs, registry metadata |
| D006 | Redis for cache/queues/locks | Low-latency coordination |
| D007 | Celery (or compatible) workers for long jobs | Training/HPO/EDA must be async |
| D008 | MLflow for experiments + registry (initially) | Industry standard; can abstract behind ATLAS interfaces |
| D009 | MinIO (S3-compatible) for artifacts | Local/dev parity with cloud object storage |
| D010 | Docker from Day 1; Kubernetes-ready manifests/Helm | Production path from the start |
| D011 | JWT + OAuth + RBAC + API keys | Enterprise auth model |
| D012 | Plugin architecture (entry-point / manifest based) | Extensibility without core forks |
| D013 | `idea.md` is the single source of truth | Architectural consistency across all work |
| D014 | Clean Architecture + SOLID + DDD (bounded contexts) | Maintainability at enterprise scale |
| D015 | MIT License | Open collaboration-friendly |
| D016 | ATLAS is an AAEP (five-layer architecture) | Elevates scope beyond AutoML to full autonomous AI engineering |
| D017 | NL never executes directly; Workflow Compiler required | Safety, auditability, optimization, reproducible plans |
| D018 | Knowledge Graph as first-class intelligence substrate | Powers recommendations, lineage, and agent reasoning |
| D019 | Multi-tier Agent Memory (STM/LTM + scoped memories) | Context quality without unbounded prompt stuffing |
| D020 | Meta Learning before exhaustive model search | Cut cost/time; reuse org/global experiment knowledge |
| D021 | Resource Scheduler owns GPU/CPU quotas & preemption | Multi-tenant fairness and production utilization |
| D022 | Feature Store (online + offline) is a platform capability | Feature reuse, lineage, low-latency serving |
| D023 | Dataset Version Control (branch/snapshot/lineage) | Reproducibility and safe experimentation on data |
| D024 | Ray is primary distributed compute fabric (Dask/Spark/Torch adapters) | Unified distributed jobs; adapters for ecosystem tools |
| D025 | Governance Layer is mandatory for production autonomy | Enterprise trust, compliance, Responsible AI |
| D026 | Plugin + Workflow Marketplaces | Ecosystem growth without core forks |
| D027 | Visual Workflow Builder (React Flow–class) | Power users + transparency of compiled DAGs |
| D028 | OpenAPI is SDK source of truth (generator) | Consistent multi-language clients |
| D029 | Autonomous Improvement Engine is closed-loop | Platform learns from outcomes, not only from prompts |
| D030 | Product editions (v1–v3, Enterprise, Cloud, Edge, Research) | Clear packaging without forking architecture |

**Supersession rule:** New decisions may *extend* earlier ones (e.g., D024 extends D007/D010 for distributed scale) but must not silently contradict them. If a contradiction is required, mark the old decision **Superseded by Dxxx** in this table.

---

## 6. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ATLAS Web Dashboard (apps/web)                   │
│  Projects · Datasets · Pipelines · Experiments · Models · Deploy · Chat │
└───────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTPS / SSE / WS
┌───────────────────────────────────▼─────────────────────────────────────┐
│                    API Gateway / Modular Monolith (apps/api)             │
│         Auth · Tenancy · REST/OpenAPI · Webhooks · Rate Limits          │
└─┬─────────┬─────────┬─────────┬─────────┬─────────┬─────────┬───────────┘
  │         │         │         │         │         │         │
  ▼         ▼         ▼         ▼         ▼         ▼         ▼
┌─────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌──────┐ ┌────────┐ ┌──────────┐
│Auth │ │Data  │ │Pipeline│ │Train │ │Eval/ │ │Deploy  │ │Monitor/  │
│Ctx  │ │Ctx   │ │Ctx     │ │Ctx   │ │XAI   │ │Ctx     │ │Retrain   │
└─────┘ └──────┘ └───┬───┘ └──────┘ └──────┘ └────────┘ └──────────┘
                     │
         ┌───────────▼───────────┐
         │  Agent Orchestrator   │
         │  (LangGraph-style /   │
         │   custom planner)     │
         └───────────┬───────────┘
                     │ structured messages
    ┌────────────────┼────────────────────────────────┐
    ▼       ▼        ▼        ▼        ▼       ▼      ▼
  Dataset Cleaning Feature Model  HPO  Train Eval … Docs
  Agents  Agents  Agents  Select …

┌─────────────────────────────────────────────────────────────────────────┐
│ Data Plane: PostgreSQL · Redis · MinIO · MLflow · Kafka (phase+) · GPU  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Evolution Path (Monolith → Microservices)

Each `services/<context>` is a bounded context with:

- Own domain models, application services, repositories  
- Clear public API (Python package interface + future HTTP)  
- No cross-context DB joins (shared DB allowed early; schemas/namespaces isolated)  
- Extraction checklist: own DB schema → own deployable → own queue → own SLO  

### AAEP Five-Layer Overlay

The diagram above remains the **modular monolith composition view**. The AAEP view organizes the same system into five layers—Experience, Intelligence, Execution, Infrastructure, Governance—detailed in §31. Layers are logical; they do not replace bounded contexts.

---

## 7. Folder Structure

```
ATLAS/
├── idea.md                 # THIS FILE — source of truth
├── README.md
├── ROADMAP.md
├── ARCHITECTURE.md
├── CONTRIBUTING.md
├── LICENSE
├── CODE_OF_CONDUCT.md
├── .editorconfig
├── .gitignore
├── .env.example
├── pyproject.toml          # uv workspace root
├── pnpm-workspace.yaml
├── docker-compose.yml
├── Makefile
│
├── apps/
│   ├── api/                # FastAPI entry (composition root)
│   ├── web/                # Frontend dashboard
│   ├── worker/             # Async job workers
│   ├── cli/                # ATLAS CLI (AAEP Experience Layer)
│   └── vscode-extension/   # VS Code extension (later)
│
├── services/               # Bounded contexts (microservice candidates)
│   ├── identity/           # Auth, users, RBAC, API keys, tenancy
│   ├── catalog/            # Projects, datasets, connectors
│   ├── profiling/          # Dataset understanding / EDA
│   ├── preparation/        # Cleaning + feature engineering
│   ├── modeling/           # Selection, training, HPO
│   ├── evaluation/         # Metrics, comparison, leaderboards
│   ├── explainability/     # SHAP/LIME/fairness
│   ├── registry/           # Model registry, stages, approvals
│   ├── serving/            # Deployment, inference APIs
│   ├── observability/      # Monitoring, drift, alerts
│   ├── orchestration/      # Workflow engine + NL compiler
│   ├── documentation/      # Model cards, reports
│   ├── cost/               # Cost estimation & recommendations
│   ├── plugins_host/       # Plugin discovery & sandboxing
│   ├── knowledge_graph/    # Entity/relationship intelligence graph (AAEP)
│   ├── memory/             # Agent memory services (AAEP)
│   ├── meta_learning/      # Cross-experiment learning (AAEP)
│   ├── scheduler/          # Resource scheduler (AAEP)
│   ├── feature_store/      # Online/offline feature store (AAEP)
│   ├── data_versioning/    # Dataset VCS (AAEP)
│   ├── synthetic/          # Synthetic data engine (AAEP)
│   ├── rag/                # RAG builder (AAEP)
│   ├── prompt_studio/      # Prompt engineering studio (AAEP)
│   ├── llm_eval/           # LLM evaluation framework (AAEP)
│   ├── research_mode/      # Paper → pipeline research mode (AAEP)
│   ├── marketplace/        # Plugin & workflow marketplace (AAEP)
│   ├── collaboration/      # Teams, comments, presence (AAEP)
│   ├── security_ai/        # AI security detections (AAEP)
│   ├── responsible_ai/     # Bias, fairness, PII, compliance (AAEP)
│   ├── analytics/          # Enterprise analytics (AAEP)
│   ├── improvement/        # Autonomous improvement engine (AAEP)
│   └── chaos/              # Chaos engineering experiments (AAEP)
│
├── agents/                 # Specialized AI agents
│   ├── orchestrator/
│   ├── dataset_understanding/
│   ├── data_cleaning/
│   ├── feature_engineering/
│   ├── model_selection/
│   ├── hyperparameter_optimization/
│   ├── training/
│   ├── evaluation/
│   ├── explainability/
│   ├── deployment/
│   ├── monitoring/
│   ├── retraining/
│   ├── documentation/
│   └── assistant/
│
├── packages/               # Shared libraries
│   ├── atlas-core/         # Domain primitives, errors, IDs
│   ├── atlas-contracts/    # Pydantic/JSON schemas, events
│   ├── atlas-db/           # SQLAlchemy/Alembic shared tooling
│   ├── atlas-storage/      # Object storage abstractions
│   ├── atlas-ml/           # ML utilities & adapters
│   ├── atlas-telemetry/    # Logging, metrics, tracing
│   ├── atlas-ui/           # Shared frontend components (optional)
│   ├── atlas-sdk-python/   # Python SDK (generated/maintained)
│   ├── atlas-sdk-js/       # JavaScript/TypeScript SDK
│   └── atlas-workflow-compiler/  # NL → DAG compiler library
│
├── sdks/                   # Published client SDKs (Python, JS/TS, Java, Go, C#)
├── plugins/                # First-party + example plugins
│   ├── connectors/
│   ├── algorithms/
│   ├── metrics/
│   ├── notifications/
│   ├── explainability/
│   ├── agents/
│   ├── preprocessors/
│   ├── deployment_targets/
│   └── visual_components/
│
├── infrastructure/
│   ├── docker/
│   ├── k8s/
│   ├── helm/atlas/
│   └── monitoring/         # Prometheus / Grafana assets
│
├── configs/                # Default configs, profiles
├── docs/                   # Extended documentation
├── scripts/                # Dev & ops scripts
└── tests/                  # Cross-cutting integration/e2e
```

> **Note:** AAEP service folders above are **architectural reservations**. Physical scaffold for Phase 0 remains as created; new directories are materialized when their phase begins—do not invent parallel conflicting trees.

---

## 8. Technology Stack

### Backend / ML

| Layer | Technology |
|-------|------------|
| Language | Python ≥3.11 (3.12+ preferred) |
| Package manager | `uv` |
| API | FastAPI, Pydantic v2, Uvicorn |
| ORM / migrations | SQLAlchemy 2.x, Alembic |
| DB | PostgreSQL 15+ (Compose default 15-alpine; 16+ preferred in prod) |
| Cache / broker | Redis |
| Workers | Celery (+ Redis/RabbitMQ); Ray Tune optional for HPO |
| Streaming (later) | Kafka / Redpanda |
| Experiments | MLflow Tracking + Model Registry |
| Artifacts | MinIO (S3 API) |
| ML libs | scikit-learn, XGBoost, LightGBM, CatBoost, PyTorch, TF (optional), HF Transformers |
| HPO | Optuna, Ray Tune |
| Explainability | SHAP, LIME |
| Agents / LLM | Structured planner (LangGraph or equivalent), provider-agnostic LLM client |
| Federated (later) | Flower / TFF / PySyft evaluation |
| Distributed compute (AAEP) | Ray (primary); Dask, Spark, Torch Distributed, DeepSpeed, Accelerate adapters |
| Graph store (AAEP) | PostgreSQL recursive/closure + optional Neo4j/Neptune later |
| Vector store (AAEP) | pgvector initially; dedicated vector DB when scale requires |
| Feature store (AAEP) | Internal service; Feast-compatible concepts |
| Workflow UI (AAEP) | React Flow (or equivalent) |

### Frontend

| Layer | Technology |
|-------|------------|
| Runtime | Node.js Latest LTS |
| Package manager | `pnpm` |
| Framework | Next.js (App Router) + TypeScript |
| UI | Accessible component system; expressive typography; CSS variables |
| Charts | Recharts / ECharts / Plotly as needed |
| State | TanStack Query + lightweight client state |
| Collaboration (later) | CRDT/presence channel (Liveblocks-class or custom WS) |

### DevOps

| Layer | Technology |
|-------|------------|
| Containers | Docker, Docker Compose |
| Orchestration | Kubernetes + Helm |
| CI/CD | GitHub Actions (planned) |
| Observability | OpenTelemetry, Prometheus, Grafana |
| Secrets | Env + K8s Secrets / external vault (later) |
| Chaos (later) | Litmus/Chaos Mesh–compatible experiments |

### Experience Clients (AAEP Target)

| Client | Status target |
|--------|----------------|
| Web Dashboard | v1 |
| REST/OpenAPI | v1 |
| CLI | v1.x |
| Python SDK | v1.x |
| JS/TS SDK | v1.x |
| GraphQL | v2+ |
| Java / Go / C# SDKs | v2+ (OpenAPI generator) |
| VS Code / Jupyter extensions | v2 |
| Mobile companion | Future |

---

## 9. Coding Conventions

- **Python:** Ruff (lint+format), mypy (strict gradually), pytest, Conventional Commits  
- **TypeScript:** ESLint + Prettier, strict `tsconfig`  
- **Architecture:** Controllers → Application services → Domain → Infrastructure adapters  
- **Naming:** `snake_case` Python, `camelCase` TS, `kebab-case` packages/dirs where conventional  
- **Errors:** Typed domain errors; map to HTTP problem details  
- **IDs:** UUIDv7 (or ULID) for time-sortable entities  
- **Config:** 12-factor; no secrets in git  
- **Tests:** Unit at domain; integration at service boundaries; e2e for critical flows  
- **Agents:** Input/output must be validated Pydantic models in `atlas-contracts`  
- **No shortcuts** that sacrifice maintainability when a clean design is feasible  
- **Compiler outputs:** Workflow DAGs are versioned artifacts; never “prompt-only” production runs  
- **Memory/Graph writes:** Must be tenant-scoped and auditable  

---

## 10. UI Design Principles

- One clear composition per primary view; avoid dashboard clutter in marketing/hero surfaces  
- Brand-first product identity for ATLAS surfaces  
- Purpose-driven typography; CSS variables for theme tokens  
- Atmosphere via subtle depth/gradients/patterns—not flat only, not generic “AI purple”  
- One job per section; reduce competing chrome  
- Real visual anchors for data/model context (charts of *this* run, not decorative noise)  
- Motion for hierarchy and feedback (2–3 intentional motions on key flows)  
- Full responsive desktop + mobile for core workflows  
- Accessibility: WCAG 2.2 AA target  
- **Visual Workflow Builder:** nodes must reveal compiled semantics (not opaque magic boxes)  
- **Explainability Dashboard:** interactive exploration over static screenshots  
- **Enterprise Analytics:** organization health first; vanity metrics last  

---

## 11. Backend Architecture (Modular Monolith)

### Composition Root (`apps/api`)

- Wires dependency injection  
- Mounts routers per bounded context  
- Owns middleware: auth, tenancy, rate limit, request ID, CORS  

### Bounded Context Rules

1. Cross-context communication via application services or domain events (not random imports of internals).  
2. Shared kernel only in `packages/atlas-core` and `packages/atlas-contracts`.  
3. Persistence: logical schemas per context (`identity`, `catalog`, `modeling`, …).  
4. Long-running work enqueued to `apps/worker`; API returns job IDs.  

### Event Model (initial)

- `DatasetUploaded`, `ProfilingCompleted`, `PipelinePlanned`, `RunStarted`, `RunCompleted`, `ModelRegistered`, `DeploymentApproved`, `DriftDetected`, `RetrainTriggered`  

### Event Model (AAEP extensions)

- `WorkflowCompiled`, `WorkflowValidated`, `WorkflowOptimized`  
- `MemoryUpserted`, `GraphEntityLinked`  
- `MetaRecommendationIssued`  
- `ScheduleGranted`, `SchedulePreempted`, `QuotaExceeded`  
- `FeatureMaterialized`, `FeatureServed`  
- `DatasetBranchCreated`, `DatasetSnapshotTaken`  
- `DriftFeedbackIngested`, `ImprovementPolicyUpdated`  
- `SecurityFindingRaised`, `RaiReportGenerated`  

---

## 12. Database Schema Overview (Logical)

**identity:** users, orgs/tenants, roles, permissions, api_keys, sessions, audit_logs  

**catalog:** projects, datasets, dataset_versions, connectors, dataset_profiles  

**orchestration:** workflows, workflow_runs, agent_messages, human_approvals  

**modeling:** experiments, runs, params, metrics, artifacts_refs, hpo_studies  

**registry:** models, model_versions, stages (None/Staging/Production/Archived), approvals  

**serving:** deployments, endpoints, revisions, traffic_splits (canary/AB)  

**observability:** predictions_log (sampled), drift_reports, alerts, slo_events  

**plugins:** plugin_registry, installations, configs  

**knowledge_graph (AAEP):** nodes, edges, edge_types, graph_snapshots, embeddings_refs  

**memory (AAEP):** stm_sessions, ltm_entries, project_memory, org_memory, user_memory, experiment_memory, global_learning_memory  

**meta_learning (AAEP):** dataset_signatures, model_priors, recommendation_logs, outcome_feedback  

**scheduler (AAEP):** queues, jobs, leases, quotas, preempt_events  

**feature_store (AAEP):** feature_views, feature_versions, online_keys, offline_partitions, lineage_edges  

**data_versioning (AAEP):** dataset_branches, commits, snapshots, diffs  

**marketplace (AAEP):** listings, versions, installs, ratings  

**collaboration (AAEP):** comments, activity_events, presence_sessions  

**security_ai / responsible_ai / analytics / improvement / chaos:** findings, reports, policies, experiment_defs as needed  

Physical DDL arrives in Phase 1+ via Alembic; this section is the conceptual map.

---

## 13. Microservices (Future Extraction Map)

| Current Module | Future Service | Trigger to Extract |
|----------------|----------------|--------------------|
| identity | auth-service | Multi-product SSO / high auth QPS |
| catalog | data-service | Heavy ingest / connector fan-out |
| modeling + worker | training-service | GPU isolation / scale |
| serving | inference-gateway | Independent deploy cadence |
| observability | monitor-service | High-cardinality telemetry |
| orchestration | orchestrator-service | Multi-cluster workflows |
| knowledge_graph | graph-service | Heavy graph query / embedding fan-out |
| scheduler | scheduler-service | Cluster-wide GPU brokerage |
| feature_store | feature-service | Online serving SLO independence |
| marketplace | marketplace-service | Public multi-tenant catalog |

---

## 14. AI Agents

| Agent | Responsibility |
|-------|----------------|
| Orchestrator | Plans DAG from NL + constraints; coordinates agents |
| Dataset Understanding | Profiling, target/problem detection, leakage, EDA summary |
| Data Cleaning | Missing/dupes/outliers, encoding, scaling |
| Feature Engineering | Generation, selection, embeddings, TS features, feature store hooks |
| Model Selection | Algorithm choice from size/types/latency/explainability |
| Hyperparameter Optimization | Optuna/Bayesian/Random/Grid/Ray Tune + early stopping |
| Training | Fit models across problem types |
| Evaluation | Metrics, curves, calibration, business KPIs |
| Explainability | SHAP, LIME, counterfactuals, PDP, fairness |
| Deployment | Docker, FastAPI, ONNX, K8s/Helm, OpenAPI |
| Monitoring | Latency, drift, accuracy, resources, alerts |
| Retraining | Drift→retrain→compare→redeploy/rollback |
| Documentation | READMEs, model cards, IEEE-style reports, decks |
| Assistant | Conversational help across the platform |

### Agent Contract (mandatory)

```text
AgentRequest { run_id, context_refs, instructions, constraints, budget }
AgentResponse { status, artifacts[], metrics{}, messages[], next_hints[] }
```

All agents are **idempotent where possible**, **budget-aware** (time/cost/tokens), and **auditable**.

### AAEP Agent Runtime Hooks

Before `run`, every agent **SHOULD**:

1. Load scoped Agent Memory (§34) for the `run_id` / project / user.  
2. Query Knowledge Graph neighbors (§33) for lineage and similar entities.  
3. Request Meta Learning priors (§35) when selecting algorithms or features.  
4. Respect Decision Engine / Governance constraints (§31.2, §31.5).  

After `run`, every agent **MUST** emit structured artifacts + metrics and **MAY** write memory/graph updates via ports (never ad-hoc DB writes).

---

## 15. APIs (Public Surface — Planned)

- `POST /v1/auth/*` — login, OAuth, tokens  
- `CRUD /v1/projects`  
- `POST /v1/datasets` / connectors  
- `POST /v1/workflows` — NL or structured plan  
- `POST /v1/workflows/{id}/run`  
- `GET /v1/runs/{id}` — status, logs, artifacts  
- `GET /v1/experiments` / leaderboard  
- `POST /v1/models/{id}/approve`  
- `POST /v1/deployments`  
- `GET /v1/monitoring/{deployment_id}`  
- `POST /v1/chat` — assistant  
- `OpenAPI 3` always generated  

### AAEP API extensions (planned)

- `POST /v1/workflows/compile` — NL → DAG (no execute)  
- `POST /v1/workflows/{id}/validate|optimize`  
- `GET /v1/graph/*` — Knowledge Graph queries  
- `GET|POST /v1/memory/*` — scoped memory (authz-heavy)  
- `POST /v1/meta/recommend` — algorithm/feature priors  
- `POST /v1/scheduler/jobs` — explicit job submission  
- `CRUD /v1/features` — feature store  
- `POST /v1/datasets/{id}/branches|snapshots`  
- `POST /v1/rag/pipelines` · `POST /v1/prompts/*` · `POST /v1/llm-eval/*`  
- `POST /v1/research/papers` — Research Mode  
- `GET /v1/marketplace/*` · `GET /v1/analytics/org`  
- `POST /v1/chaos/experiments`  
- GraphQL gateway: `/graphql` (v2+)  

Versioning: URL `/v1`; breaking changes require `/v2`.

---

## 16. Security Model

- JWT access + refresh; OAuth2/OIDC providers  
- RBAC: roles (Viewer, DataScientist, MLEngineer, Approver, Admin) scoped to tenant/project  
- API keys for service-to-service and CI  
- Encryption in transit (TLS); at rest via DB/volume/object-store encryption  
- Secrets never in images or git; injected at runtime  
- Rate limiting + abuse detection  
- Audit log for authz, approvals, deployments, data access  
- Multi-tenancy: hard tenant isolation at query and storage prefix level  
- Plugin sandboxing (process/container isolation roadmap)  

### AAEP Security Extensions

See §44 AI Security and §45 Responsible AI. Security findings feed Governance and may block Workflow Compiler promotion to execute.

---

## 17. Deployment Strategy

- **Local:** Docker Compose (api, web, worker, postgres, redis, minio, mlflow)  
- **Staging/Prod:** Kubernetes via Helm chart `infrastructure/helm/atlas`  
- **Images:** multi-stage Dockerfiles under `infrastructure/docker`  
- **Releases:** immutable image tags + SBOM (planned)  
- **Progressive delivery:** approve → staging → canary → production; rollback on SLO breach  
- **Editions:** same core chart; feature flags / values toggle Cloud, Edge, Research packs (§51)  

---

## 18. DevOps Pipeline (Planned)

1. PR → lint, typecheck, unit tests  
2. Build images  
3. Integration tests (Compose)  
4. Security scan (deps + container)  
5. Deploy to staging  
6. Smoke + soak  
7. Manual/automated promote to prod  
8. **(AAEP)** Chaos experiments in staging on schedule (§49)  
9. **(AAEP)** SDK generation from OpenAPI artifact (§48)  

---

## 19. MLOps Lifecycle

```
Ingest → Profile → Clean → Features → Select → HPO → Train → Evaluate → Explain
    → Compare → Human Gate → Register → Deploy → Monitor → Drift → Retrain → …
```

Natural language instructions compile into constrained workflow DAGs with budgets and gates (e.g., “deploy only if Recall ≥ 0.95”).

**AAEP path:** NL → Workflow Compiler (§32) → AI Planning Engine (§36) → Resource Scheduler (§37) → Execution Layer engines (§31.3) → Monitoring → Autonomous Improvement (§47).

---

## 20. Module Descriptions

| Module | Description |
|--------|-------------|
| identity | Users, orgs, RBAC, API keys, sessions |
| catalog | Projects, datasets, versions, connectors (CSV/Excel/JSON/SQL/S3/…) |
| profiling | Automated EDA and data quality |
| preparation | Cleaning + feature pipelines (versioned) |
| modeling | Training, HPO, model library adapters |
| evaluation | Metrics, reports, leaderboards |
| explainability | Attribution and fairness |
| registry | Versioned models, stages, approvals |
| serving | Packaging and endpoints |
| observability | Live metrics, drift, alerts |
| orchestration | Planner, DAG runner, HITL gates |
| documentation | Generated docs and model cards |
| cost | Runtime/cost/GPU recommendations |
| plugins_host | Install/load third-party extensions |
| knowledge_graph | Cross-entity relationships for reasoning & recommendations |
| memory | Short/long-term and scoped agent memories |
| meta_learning | Priors from similar past experiments |
| scheduler | GPU/CPU quotas, preemption, distributed dispatch |
| feature_store | Online/offline features, lineage, serving |
| data_versioning | Dataset branches, snapshots, rollback, lineage |
| synthetic | GAN/CTGAN/Diffusion/VAE/TabDDPM synthetic data |
| rag | Automated RAG pipeline builder |
| prompt_studio | Prompt templates, versioning, A/B eval |
| llm_eval | Hallucination, faithfulness, safety, cost metrics |
| research_mode | Paper → methodology → experiments → reproducibility |
| marketplace | Plugin & workflow marketplace |
| collaboration | Teams, comments, live presence, activity |
| security_ai | Prompt injection, poisoning, adversarial, secret scans |
| responsible_ai | Bias, fairness, PII, GDPR, model cards, risk |
| analytics | Org-wide platform analytics |
| improvement | Closed-loop autonomous improvement |
| chaos | Controlled failure injection & recovery verification |

---

## 21. Roadmap (Summary)

See `ROADMAP.md` for detail. Phases:

0. Foundation ✅  
1. Project foundation & tooling ✅  
2. Authentication & tenancy  
3. Dataset ingestion  
4. Dataset analysis  
5. Cleaning pipeline  
6. Feature engineering  
7. Training engine  
8. HPO  
9. Experiment tracking  
10. Explainability  
11. Deployment  
12. Monitoring  
13. Multi-agent orchestration  
14. Plugin ecosystem  
15. Federated learning  
16. Enterprise features  
17. Production hardening  
18. Public launch docs  

### Enterprise Version Plan (additive — does not replace phases 0–18)

| Version / Edition | Theme | Anchors |
|-------------------|--------|---------|
| **ATLAS v1.0** | Core AAEP path for tabular ML | Phases 1–13 subset: ingest→train→register→deploy→monitor; Workflow Compiler v1; REST+Web+CLI |
| **ATLAS v2.0** | Intelligence depth | Knowledge Graph, Agent Memory, Meta Learning, Feature Store, Data VCS, Visual Builder, SDKs |
| **ATLAS v3.0** | GenAI + Research | RAG Builder, Prompt Studio, LLM Eval, Research Mode, Distributed Training at scale |
| **ATLAS Enterprise** | Governance & tenancy at scale | SSO/SCIM, hard isolation, RAI compliance packs, audit exports, quotas, analytics |
| **ATLAS Cloud** | Managed multi-tenant SaaS | Control plane, billing, regional residency, marketplace hosting |
| **ATLAS Edge** | Constrained/on-prem inference | Slim serving + offline sync + air-gap install |
| **ATLAS Research** | Scientific reproducibility | Paper ingestion, experiment cloning, IEEE-style reports |

Full narrative: §51.

---

## 22. Future Improvements

- Feature store (Feast or internal)  
- Vector DB for RAG over experiments/docs  
- Multi-cloud cost broker  
- On-prem air-gapped install  
- Marketplace for plugins and model templates  
- Continuous evaluation of LLM planners  
- GraphQL federation gateway  
- Mobile companion app  
- Carbon-aware scheduling policies  
- Cross-org federated meta-learning (privacy-preserving)  
- Formal verification of critical workflow policies  

---

## 23. Pending Tasks

### Completed (Phase 0)

- [x] Git monorepo on `main` at Desktop/ATLAS  
- [x] `idea.md` source of truth + core docs  
- [x] MIT license, CoC, `.gitignore`, `.editorconfig`  
- [x] Full folder structure with service/agent/package placeholders  
- [x] Docker/K8s/Helm/monitoring skeletons  
- [x] Example plugin manifests  
- [x] AAEP architecture expansion recorded in `idea.md` (five layers + major modules)  

### Completed (Phase 1)

- [x] Expand `uv` workspace members and package metadata  
- [x] Scaffold Next.js app under `apps/web`  
- [x] FastAPI health/live/ready/metrics + DI shell  
- [x] Full Docker Compose (api, web, worker, postgres, redis, minio, mlflow, prometheus, grafana)  
- [x] OpenTelemetry hook + structured logging + Prometheus metrics  
- [x] Expand CI (lint, typecheck, tests, Docker builds)  
- [x] Flesh out Helm templates for api/web/worker shell  
- [x] Alembic foundation revision (no domain tables)  
- [x] MinIO storage port/adapter + MLflow URI abstraction  
- [x] Local verification of Compose health + quality gates for **v0.1.0 Platform Foundation**  

### Completed (Phase 2)

- [x] Identity context + JWT auth (access + rotating refresh)  
- [x] OAuth/OIDC hooks (provider list stub)  
- [x] RBAC + tenancy (org + project membership)  
- [x] API keys (hashed, rotatable, revocable)  
- [x] Audit log foundation  

### Completed (Phase 3)

- [x] Project CRUD (catalog) + dataset upload  
- [x] MinIO-backed dataset versions (immutable)  
- [x] Connector interfaces (SQL, S3 stubs)  
- [x] Dataset metadata catalog + search/filter  

### Completed (Phase 4)

- [x] Profiling pipeline (dtypes, nulls, distributions, correlations)  
- [x] Target / problem-type heuristics  
- [x] Leakage heuristics  
- [x] Dataset Understanding Agent (deterministic + optional LLM)  
- [x] EDA report artifacts in MinIO  

### Completed (Phase 5)

- [x] Missing values, duplicates, outliers strategies  
- [x] Versioned preparation recipes (HITL approve → new catalog version)  
- [x] Data Cleaning Agent  
- [ ] Encoding / scaling pipelines *(Phase 6 Feature Engineering)*  

### Next (Phase 6 — do not start until instructed)

- [ ] Feature generation & selection baselines  
- [ ] Time-series / text feature hooks  
- [ ] Feature Engineering Agent  
- [ ] Feature store interface (stub)  

### Architecture notes (Phase 3)

- **Projects SoT:** `catalog.projects` owns datasets. `identity.projects` retained from Phase 2 for legacy RBAC scaffolding; application `/v1/projects` is catalog.  
- **D023:** Phase 3 ships linear immutable versions; branch/snapshot UI deferred.  
- **Statistics:** `dataset_statistics` holds row/column *estimates* only — not Phase 4 EDA.

### Architecture follow-ups (docs/design)

- [ ] ADR series for Workflow Compiler, Knowledge Graph store choice, Scheduler semantics  
- [ ] Formal Pydantic agent contracts expansion beyond stubs  
- [ ] Materialize reserved AAEP service packages when their phase begins  

### Later (tracked in ROADMAP.md)

- [ ] Dataset upload + MinIO-backed versions  
- [ ] Dataset Understanding Agent (first real agent)  
- [ ] Workflow Compiler MVP  
- [ ] Resource Scheduler MVP  
- [ ] Feature Store MVP  
- [ ] Meta Learning priors v0  

---

## 24. Technical Debt

*(Log debt here as it appears; never leave silent.)*

| ID | Item | Mitigation |
|----|------|------------|
| TD001 | Host `pnpm` / Corepack EPERM on some Windows machines | Use `npm` locally; Docker/CI use `pnpm` via Corepack / `pnpm/action-setup` |
| TD002 | Compose verification requires Docker Desktop running | Document in README; CI builds images even if local daemon is down |
| TD003 | MLflow Compose uses SQLite + local volume for simplicity | Replace with Postgres backend store before heavy multi-user experiment load |
| TD004 | Next.js ESLint config is minimal during Phase 1 | Expand to full `eslint-config-next` flat config in Phase 2 polish |
| TD006 | Docker Hub/GHCR TLS failures on some hosts | Prefer cached base tags; host-fetch MinIO/Prometheus/Grafana via `scripts/dev/fetch-binaries.ps1`; mitigated for v0.1.0 verification |
| TD007 | Compose defaults to `postgres:15-alpine` when 16 cannot be pulled | Align to Postgres 16 when registry access is healthy; both supported by SQLAlchemy |
| TD008 | Celery worker healthcheck uses `inspect ping` (hostname-sensitive) | Acceptable for Phase 1; replace with lighter liveness probe if flaky in CI |
| TD009 | `identity.projects` coexists with `catalog.projects` | Prefer catalog SoT; consider deprecation migration later |
| TD010 | pytest-cov not in workspace; Phase 3 coverage not machine-measured | Add `pytest-cov` in a tooling polish PR if gating on % |
| TD011 | Docker Desktop engine can return HTTP 500 after heavy local image builds/WSL stress; Compose ops stall until Desktop restart | Separate infra from app bugs; restart Docker Desktop, then `docker compose up -d` |
| TD012 | Phase 4 API must ship `celery` client to publish tasks; worker package is not installed in API image (by design) | Keep broker publish via `Celery.send_task`; never import `atlas_worker` from API |

---

## 25. Known Issues

| ID | Issue | Status |
|----|-------|--------|
| KI001 | Local Docker registry TLS errors (`http: server gave HTTP response to HTTPS client`) can prevent image pulls | Open — environment/network; not an ATLAS code defect |

---

## 26. Research Notes

- Evaluate LangGraph vs custom FSM for orchestrator reliability under tool failures.  
- Prefer Optuna first for HPO; Ray Tune when distributed trials are required.  
- Keep MLflow behind an interface (`ExperimentTracker` port) to allow swap.  
- For leakage detection, combine schema heuristics + temporal split checks + correlation-to-target red flags.  
- ONNX export as default portable artifact where supported; PyTorch/sklearn pickle only inside controlled runtimes.  
- Knowledge Graph: start with relational + pgvector; introduce Neo4j only if query patterns demand it.  
- Agent Memory: hybrid keyword + embedding retrieval with strict token budgets.  
- Meta Learning: dataset fingerprinting (schema stats + embedding of profile summary) → kNN over past wins.  
- Scheduler: Kubernetes as substrate; ATLAS scheduler as policy layer (quotas, fair-share, preemption reasons).  
- Workflow Compiler: separate *plan IR* from *runtime DAG* so optimization passes are testable without LLMs.  

---

## 27. Dataset Support (Target)

CSV, Excel, JSON, Parquet, PostgreSQL, MySQL, MongoDB, S3, Azure Blob, GCS, Kaggle.

## 28. ML Problem Types (Target)

Regression, Classification, Clustering, Recommendation, Time Series, NLP, CV, Audio, Multimodal, Anomaly Detection.

## 29. Continuous Improvement Protocol

On every feature:

1. Read `idea.md` first.  
2. Implement without contradicting locked decisions (or explicitly revise this file).  
3. Update this file for architecture, modules, stack, or roadmap changes.  
4. Note new debt, risks, and research findings.  

---

# AAEP Architecture Expansion

*Sections §30–§51 extend ATLAS into a world-class Autonomous AI Engineering Platform. They preserve and refine—not replace—§1–§29.*

---

## 30. Autonomous AI Engineering Platform (AAEP)

### Definition

**ATLAS — Autonomous AI Engineering Platform** is an intelligent platform that can **plan, build, deploy, monitor, improve, and govern** AI systems with minimal manual engineering, while remaining inspectable and controllable by humans.

ATLAS is **not merely AutoML**. AutoML optimizes model search. An AAEP:

| Capability | AutoML (typical) | ATLAS AAEP |
|------------|------------------|------------|
| Problem framing | Manual | NL → Intent + constraints via Workflow Compiler |
| Pipeline construction | Fixed templates | Dynamic planning + DAG optimization |
| Organizational learning | Weak | Knowledge Graph + Meta Learning + Memory |
| Deployment & ops | Often bolted on | First-class Execution + Monitoring + Retraining |
| Governance | Optional | Mandatory Governance Layer |
| Ecosystem | Closed | Plugins + Workflow Marketplace |
| Continuous improvement | Rare | Autonomous Improvement Engine |

### Comparable Ambition

Architectural ambition aligned with Google Vertex AI, Amazon SageMaker, Databricks, Kubeflow, and modern AI operating systems—differentiated by a **compiler-mediated multi-agent control plane**, explicit **memory/graph intelligence**, and **governed autonomy**.

### Autonomy Levels (Operational)

| Level | Name | Behavior |
|-------|------|----------|
| L0 | Assisted | Human drives; Assistant advises |
| L1 | Compiled | NL → DAG; human starts runs |
| L2 | Orchestrated | Agents execute DAG; HITL at deploy |
| L3 | Closed-loop | Monitor → retrain within policy |
| L4 | Self-improving | Improvement Engine updates priors/policies (still gated) |

Production default: **L2**, with L3/L4 enabled per tenant policy.

---

## 31. Five Core Layers

```
┌──────────────────────────────────────────────────────────┐
│                 1. EXPERIENCE LAYER                       │
│  Web · REST · GraphQL · CLI · SDKs · IDE · Jupyter · App │
└────────────────────────────┬─────────────────────────────┘
┌────────────────────────────▼─────────────────────────────┐
│                 2. INTELLIGENCE LAYER                     │
│  Agents · Planner · Compiler · Graph · Memory · Meta ·   │
│  Recommend · Assistant · Prompts · Decisions             │
└────────────────────────────┬─────────────────────────────┘
┌────────────────────────────▼─────────────────────────────┐
│                 3. EXECUTION LAYER                        │
│  Pipelines · Data · Features · Train · HPO · DistTrain · │
│  Scheduler · Deploy · Monitor · Retrain                  │
└────────────────────────────┬─────────────────────────────┘
┌────────────────────────────▼─────────────────────────────┐
│                 4. INFRASTRUCTURE LAYER                   │
│  K8s · Docker · PG · Redis · Kafka · MLflow · MinIO ·    │
│  Ray · Celery · Prom/Grafana · OTel · Object Store · GPU │
└────────────────────────────┬─────────────────────────────┘
┌────────────────────────────▼─────────────────────────────┐
│                 5. GOVERNANCE LAYER                       │
│  RBAC · Audit · Compliance · Security · Cost · Carbon ·  │
│  Registry · VCS · HITL · RAI · Bias · Fairness           │
└──────────────────────────────────────────────────────────┘
```

All user intent enters via Experience; **all autonomous action is proposed by Intelligence, enacted by Execution, hosted by Infrastructure, and constrained by Governance**.

### 31.1 Experience Layer

Surfaces through which humans and external systems interact with ATLAS:

| Surface | Role |
|---------|------|
| Web Dashboard | Primary product UX: projects, data, workflows, experiments, deploy, monitor, chat |
| REST API | Canonical machine interface; OpenAPI 3 source of truth |
| GraphQL (future) | Flexible read models for complex UI queries |
| CLI | Automation, CI, power users (`atlas` command) |
| Python SDK | Native data-science workflow integration |
| JavaScript / TypeScript SDK | Web/app integrations |
| Java SDK | Enterprise JVM ecosystems |
| VS Code Extension | Inline experiments, dataset peek, run status |
| Jupyter Extension | Magics / widgets for notebook-native ATLAS runs |
| Mobile Companion (future) | Approvals, alerts, monitoring glance |

Experience components **must not** embed business rules that bypass Governance or the Workflow Compiler.

### 31.2 Intelligence Layer

The cognitive control plane. **All intelligence flows through this layer** before side effects.

| Component | Responsibility |
|-----------|----------------|
| Multi-Agent System | Specialist agents (§14) collaborating under contracts |
| LLM Planner | Decomposes goals into candidate task graphs |
| Workflow Compiler | NL → Intent → Constraints → Plan IR → DAG (§32) |
| Knowledge Graph | Entity/relationship substrate (§33) |
| Agent Memory | STM/LTM + scoped memories (§34) |
| Meta Learning | Priors from historical experiments (§35) |
| Recommendation Engine | Surfaces models, features, templates, plugins |
| AI Assistant | Conversational UX over the same tools/agents |
| Prompt Engine | Template management, versioning, routing (§42) |
| Decision Engine | Policy checks: gates, budgets, risk, approvals |

**Flow:** Experience event → Decision Engine (authz/policy) → Memory+Graph retrieval → Planner/Compiler → validated DAG → Execution handoff → outcomes written back to Memory/Graph/Meta Learning.

### 31.3 Execution Layer

Deterministic engines that perform work. Intelligence *decides*; Execution *does*.

| Engine | Responsibility |
|--------|----------------|
| Pipeline Engine | Runs DAGs, checkpoints, retries |
| Dataset Engine | Ingest, validate, profile hooks, format I/O |
| Feature Store | Materialize, serve, validate features (§39) |
| Training Engine | Fit models via adapters |
| Hyperparameter Optimization | Search studies (Optuna/Ray Tune) |
| Distributed Training | Multi-GPU/node via Ray/Torch/DeepSpeed/Accelerate (§38) |
| Resource Scheduler | Placement, quotas, preemption (§37) |
| Deployment Engine | Package, roll out, traffic split |
| Monitoring Engine | Live metrics, drift, alerts |
| Retraining Engine | Policy-driven retrain/compare/rollback |

### 31.4 Infrastructure Layer

Runtime substrate (aligned with §8 / D005–D010, D024):

Kubernetes · Docker · PostgreSQL · Redis · Kafka · MLflow · MinIO · Ray · Celery · Prometheus · Grafana · OpenTelemetry · Object Storage · GPU Workers.

Infrastructure is **swappable behind ports** where practical (e.g., managed Postgres, cloud object storage, external Ray clusters).

### 31.5 Governance Layer

Non-bypassable controls for enterprise trust:

| Control | Purpose |
|---------|---------|
| RBAC | Least-privilege actions |
| Audit Logs | Immutable who/what/when |
| Compliance | Policy packs (SOC2-oriented controls, etc.) |
| Security | Authn/z, secrets, AI security (§44) |
| Cost Tracking | Per-run / per-project spend |
| Carbon Footprint | Energy/carbon estimates for jobs |
| Model Registry | Stages, approvals, lineage |
| Version Control | Code, workflows, datasets, prompts |
| Human Approval | Production and high-risk gates |
| Responsible AI | Bias, fairness, PII, model cards (§45) |
| Bias Detection / Fairness Analysis | Pre-deploy and continuous checks |

Governance may **reject, rewrite, or require approval** for compiled workflows before Execution.

---

## 32. AI Workflow Compiler

ATLAS **does not directly execute natural language**. NL is an authoring interface; the **Workflow Compiler** produces an auditable plan.

```
Natural Language
      ↓
Intent Extraction
      ↓
Constraint Parsing
      ↓
Planning
      ↓
Execution Graph (DAG)
      ↓
Validation
      ↓
Optimization
      ↓
Execution
      ↓
Monitoring
      ↓
Feedback
```

### Stages

1. **Natural Language** — User prompt or Assistant dialogue turn; stored as an artifact with author + tenant.  
2. **Intent Extraction** — Classify goal (train, evaluate, deploy, monitor, retrain, explain, RAG build, …); detect entities (dataset, metric, model).  
3. **Constraint Parsing** — Extract hard/soft constraints: metric thresholds, latency SLO, budget, forbidden algorithms, compliance tags (“no PII egress”), deploy gates.  
4. **Planning** — AI Planning Engine (§36) decomposes tasks, resolves dependencies, consults Meta Learning + Graph. Emits **Plan IR** (versioned JSON/Pydantic).  
5. **Execution Graph (DAG)** — Concrete nodes (agent/engine calls) and edges (data/control). Includes HITL nodes when policy requires.  
6. **Validation** — Schema checks, RBAC feasibility, data availability, quota estimates, RAI policy, cycle detection, secret scanning of params.  
7. **Optimization** — Parallelize independent nodes, prune dominated algorithms via Meta Learning, choose cost/carbon-aware resources (§43), cache reusable features.  
8. **Execution** — Pipeline Engine + Scheduler run the DAG; each node is contract-validated.  
9. **Monitoring** — Metrics, logs, traces; drift and failure signals.  
10. **Feedback** — Outcomes update Memory, Graph, Meta Learning, and Autonomous Improvement (§47).  

### Compiler Artifacts

- `workflow_source` (NL + structured overrides)  
- `plan_ir` (pre-optimization)  
- `dag_vN` (executable)  
- `validation_report`  
- `optimization_report`  

Humans can edit the DAG in the Visual Workflow Builder (§41); edits re-enter Validation.

---

## 33. Knowledge Graph

Dedicated module storing relationships that power recommendations and agent reasoning.

### Core Entity Types

Users · Organizations · Projects · Datasets · Features · Experiments · Models · Deployments · Agents · Plugins · Pipelines (Workflows)

### Example Edges

| Edge | Meaning |
|------|---------|
| `USER_MEMBER_OF` | User ↔ Organization |
| `PROJECT_OWNS_DATASET` | Project ↔ Dataset |
| `DATASET_HAS_VERSION` | Dataset ↔ DatasetVersion |
| `FEATURE_DERIVED_FROM` | Feature ↔ Dataset/Feature |
| `EXPERIMENT_USED_DATASET` | Experiment ↔ DatasetVersion |
| `EXPERIMENT_PRODUCED_MODEL` | Experiment ↔ ModelVersion |
| `MODEL_DEPLOYED_AS` | ModelVersion ↔ Deployment |
| `AGENT_EXECUTED_IN` | Agent ↔ WorkflowRun |
| `PLUGIN_USED_IN` | Plugin ↔ Pipeline/Run |
| `SIMILAR_TO` | Dataset/Model similarity (Meta Learning) |
| `APPROVED_BY` | Model/Deployment ↔ User |

### Uses

- “What worked on similar datasets?”  
- Lineage & blast-radius for bad data  
- Plugin/workflow recommendations  
- Explainability of *why* a plan was chosen  
- Enterprise Analytics rollups (§46)  

### Storage Strategy

Start: PostgreSQL tables + optional pgvector for similarity. Scale path: graph DB. All writes tenant-scoped and audited (D018, D025).

---

## 34. Agent Memory

Complete memory architecture for high-quality, budgeted context.

| Memory | Stores | Lifetime |
|--------|--------|----------|
| **Short-Term Memory (STM)** | Current run dialogue, intermediate tool results, active constraints | Run / session |
| **Long-Term Memory (LTM)** | Durable facts agents may recall (preferred metrics, known leaks, org conventions) | Months–years; consolidated |
| **Project Memory** | Project goals, dataset quirks, approved pipelines, naming conventions | Project lifetime |
| **Organization Memory** | Policies, forbidden data classes, standard SLO templates, brand/compliance rules | Org lifetime |
| **User Memory** | Individual preferences (verbosity, default metrics, IDE habits) | User lifetime (exportable/deletable for GDPR) |
| **Experiment Memory** | Per-experiment hypotheses, failure notes, “what we tried” | Experiment lifetime |
| **Global Learning Memory** | Anonymized/aggregated priors across tenants (opt-in) for Meta Learning | Platform-managed |

### Retrieval Protocol (before decisions)

1. Authorize scope (user/project/org).  
2. Fetch STM for `run_id`.  
3. Retrieve top-k LTM / project / org / experiment memories by hybrid search (keyword + embeddings).  
4. Attach Graph neighborhood summaries.  
5. Enforce token/cost budget; drop lowest-utility chunks.  
6. Log memory IDs used for audit/reproducibility.  

Agents **never** silently persist secrets or raw PII into Global Learning Memory.

---

## 35. Meta Learning Engine

ATLAS must not blindly train every algorithm.

```
Similar datasets
      ↓
Past successful models
      ↓
Recommend best algorithms
      ↓
Reduce training time
      ↓
Increase accuracy
```

### Mechanism

1. **Fingerprint** datasets: schema vector, size, imbalance, modality, leakage risk, target type.  
2. **Index** historical runs: algorithm, search space, best metrics, cost, hardware, failures.  
3. **Retrieve** nearest neighbors within tenant (and global opt-in pool).  
4. **Rank** candidates with a meta-model / heuristic ensemble (Bayesian priors acceptable in v0).  
5. **Emit** recommendation set to Model Selection + HPO (warm-start search spaces).  
6. **Close the loop** with outcome feedback (success, regret, user overrides).  

### Benefits

- Fewer wasted GPU hours  
- Faster time-to-first-good-model  
- Transfer of institutional knowledge  
- Better cold-start for new users via Global Learning Memory (privacy-preserving)  

Meta Learning advises; Governance and user constraints still bind.

---

## 36. AI Planning Engine

Builds execution graphs dynamically (used by Orchestrator + Workflow Compiler).

| Concern | Behavior |
|---------|----------|
| Task decomposition | Split goals into atomic agent/engine tasks |
| Dependency resolution | Data & control edges; enforce ordering |
| Parallel execution | Mark independent subgraphs for concurrent schedule |
| Failure recovery | Typed retries, compensating actions, skip-with-policy |
| Retry strategy | Exponential backoff, max attempts, idempotency keys |
| Checkpointing | Persist node outputs; resume mid-DAG |
| Resource planning | Estimate CPU/GPU/memory/time; consult Cost Engine |

Planner output is **Plan IR**, not free text. Deterministic planning preferred; LLM used for decomposition suggestions under schema constraints.

---

## 37. Resource Scheduler

Production-grade scheduling for multi-tenant AI workloads.

### Capabilities

- GPU scheduling (type, MIG/fractional where available)  
- CPU scheduling  
- Priority queues (interactive vs batch vs critical retrain)  
- Autoscaling hooks (K8s HPA/KEDA / Ray autoscaler)  
- Distributed workers (Celery + Ray actors)  
- Checkpoint resume after preemption  
- Preemption with reason codes  
- Job cancellation (user/admin/policy)  
- Multi-user fair-share  
- Quota enforcement (per user/project/org)  

### Placement Loop

Admit → quota check → queue → bind resources → watch → preempt/reschedule → complete → accounting (cost + carbon).

Scheduler is the **only** component that grants accelerators at scale (D021).

---

## 38. Distributed Computing

Expand Execution for large-scale training and HPO:

| Technology | Role in ATLAS |
|------------|---------------|
| Ray | Primary distributed fabric (train, tune, serve actors) |
| Dask | Parallel dataframe / pandas-scale prep |
| Apache Spark | Big data prep connectors / jobs |
| Torch Distributed | Native PyTorch multi-GPU/node |
| DeepSpeed | Memory-efficient large model training |
| Accelerate | Hugging Face–friendly distributed launcher |
| Multi-GPU / Multi-node | First-class Scheduler + Training Engine concern |

Adapters live in `atlas-ml`; Orchestrator selects backend from constraints (cluster available, model size, budget).

---

## 39. Feature Store

Enterprise Feature Store for reuse and low-latency serving.

| Capability | Description |
|------------|-------------|
| Versioning | Immutable feature view versions |
| Reuse | Cross-project share within org policy |
| Lineage | Feature ← transforms ← datasets |
| Caching | Materialization cache + Redis hot keys |
| Offline Store | Historical feature matrices for training |
| Online Store | Key-value / low-latency inference features |
| Feature validation | Drift, null spikes, schema contracts |
| Feature serving | Batch and online APIs |

Integrates with Feature Engineering Agent and Deployment/Monitoring for training–serving skew detection.

---

## 40. Data Version Control

Every dataset supports:

**Versioning · History · Branching · Rollback · Comparison · Snapshots · Lineage**

Inspired by DVC/lakehouse patterns, implemented as ATLAS `data_versioning` context:

- Branches for experimental cleans  
- Snapshots pinned by experiments  
- Diffs for schema + distribution change  
- Rollback without destroying audit history  
- Lineage edges into Knowledge Graph  

Training runs **must** pin `dataset_version_id` (and optional feature view versions).

---

## 41. Visual Workflow Builder

Drag-and-drop editor for pipelines (inspired by LangFlow, ComfyUI, Node-RED, n8n; implementation target **React Flow**).

### Node Architecture

| Node kind | Examples |
|-----------|----------|
| Source | Dataset, connector, feature view |
| Transform | Clean, featurize, split |
| Model | Train, HPO, evaluate |
| GenAI | Chunk, embed, retrieve, prompt, LLM eval |
| Control | Branch, gate/HITL, map-reduce |
| Sink | Register, deploy, notify, report |

Each node maps 1:1 to Plan IR / DAG node types. Serialization round-trips with the Workflow Compiler. Validation errors highlight nodes. Collaboration annotations attach to nodes (§41.1 via § collaboration module).

### 41.1 Live Collaboration (Experience + Collaboration Module)

Support organizations, teams, projects, shared experiments, comments, live editing, activity timeline, presence, and version history—for workflows, notebooks metadata, and model cards. Conflict policy: CRDT or OT on workflow documents; strong authz on experiments.

---

## 42. GenAI Product Modules

### 42.1 Research Mode

User uploads a research paper. ATLAS:

1. Extracts methodology (models, metrics, datasets, splits)  
2. Downloads or locates datasets (licensed connectors)  
3. Implements a pipeline (Compiler + agents)  
4. Runs experiments under budget  
5. Compares to reported results  
6. Generates a reproducibility report (Documentation Agent)  

### 42.2 Synthetic Data Engine

Beyond SMOTE: **GAN · CTGAN · Diffusion · VAE · TabDDPM · privacy-preserving generation · balancing · augmentation**. Outputs are versioned datasets with provenance “synthetic” flags and RAI review hooks.

### 42.3 RAG Builder

Automated RAG pipelines for PDF, DOCX, websites, knowledge bases—covering embedding generation, chunking, retrieval, reranking, evaluation, and deployment. Uses vector store + Serving Engine.

### 42.4 Prompt Engineering Studio

Prompt templates, versioning, comparison, evaluation, latency, cost, and A/B testing—backed by Prompt Engine and LLM Evaluation Framework.

### 42.5 LLM Evaluation Framework

Measures: hallucination, faithfulness, groundedness, latency, token usage, cost, safety, bias, toxicity. Results gate promotion like classical ML metrics.

---

## 43. Cost Optimization Engine

Estimates and optimizes:

Cloud cost · Training cost · GPU recommendation · Runtime · Memory · Energy usage · Carbon footprint  

Recommends the cheapest infrastructure that satisfies constraints (latency, accuracy gates, region, compliance). Integrates with Scheduler quotas and Governance cost policies. Feeds optimization pass of Workflow Compiler.

---

## 44. AI Security

Threat-aware controls beyond classic AppSec:

| Control | Purpose |
|---------|---------|
| Prompt Injection Detection | Protect Compiler/Assistant/tool use |
| Data Poisoning Detection | Training/data integrity signals |
| Model Theft Detection | Exfiltration / suspicious download patterns |
| Adversarial Attack Detection | Inference-time attack signals |
| Membership Inference Detection | Privacy risk indicators |
| Secret Scanning | Prompts, configs, notebooks, logs |
| Dependency Scanning | Supply chain CVEs |
| Security Score | Roll-up for projects/models/deployments |

Findings can block Execution or require Approver role.

---

## 45. Responsible AI

| Capability | Notes |
|------------|-------|
| Bias Detection | Pre/post training |
| Fairness Metrics | Configurable group fairness |
| Explainability | Tied to §46 dashboard |
| PII Detection | Datasets, prompts, logs |
| GDPR | Access, export, delete, memory erasure |
| Model Cards | Auto-generated + editable |
| Risk Assessment | Tiered risk → HITL requirements |
| Compliance Reports | Exportable audit packs |

---

## 46. Explainability Dashboard & Enterprise Analytics

### Explainability Dashboard

Interactive SHAP · Feature Timeline · Counterfactual Explorer · Decision Paths · Error Explorer · Model Evolution · Confidence Analysis.

### Enterprise Analytics

Organization-wide dashboards: users, projects, GPU utilization, model usage, inference requests, training jobs, deployments, cloud spending, success rate, carbon footprint, platform health.

---

## 47. Autonomous Improvement Engine

Closed-loop system that improves ATLAS itself:

**Inputs:** previous experiments, failures, deployment outcomes, drift reports, user feedback, agent performance.  

**Actions:** update Meta Learning priors, adjust Compiler optimization heuristics, tune Scheduler fair-share, deprecate underperforming templates, propose prompt/template upgrades.  

**Controls:** all self-modifications are versioned, A/B tested when possible, and subject to Governance (no silent production policy changes).

---

## 48. Plugin Marketplace, Workflow Marketplace & SDK Generator

### Plugin Marketplace

Extends D012: algorithms, preprocessors, metrics, agents, connectors, deployment targets, notifications, visual components, custom models—plus a **Plugin SDK** and hosted/on-prem marketplace.

### Workflow Marketplace

Users publish pipelines, templates, workflows, experiments, and reusable AI systems (with licensing + security review).

### API SDK Generator

OpenAPI specs generate SDKs for **Python, JavaScript, TypeScript, Java, Go, C#**. Generated clients publish from CI; hand-written ergonomics allowed in wrappers without drifting from OpenAPI (D028).

---

## 49. Chaos Engineering

Resilience verification for AAEP production readiness:

Worker failures · Container failures · Node failures · Database outages · Network failures · Automatic recovery validation.

Chaos experiments run primarily in non-prod; production game-days require explicit approval. Results feed Improvement Engine and SLO error budgets (§17–§18).

---

## 50. Mapping: Layers ↔ Existing Bounded Contexts

| Layer | Primary contexts / packages |
|-------|-----------------------------|
| Experience | `apps/web`, `apps/api`, `apps/cli`, `sdks/*`, extensions |
| Intelligence | `orchestration`, `agents/*`, `knowledge_graph`, `memory`, `meta_learning`, `prompt_studio`, `atlas-workflow-compiler` |
| Execution | `catalog`, `profiling`, `preparation`, `modeling`, `evaluation`, `feature_store`, `scheduler`, `serving`, `observability`, `rag`, `synthetic`, `research_mode` |
| Infrastructure | `infrastructure/*`, Redis/PG/MinIO/MLflow/Kafka/Ray/Celery |
| Governance | `identity`, `registry`, `cost`, `security_ai`, `responsible_ai`, `documentation`, HITL in `orchestration` |

This mapping preserves the modular monolith extraction path (§13).

---

## 51. Enterprise Roadmap (Versions & Editions)

Delivery still follows **phases 0–18** in §21 / `ROADMAP.md`. Versions package those phases for stakeholders:

### ATLAS v1.0 — “Governed Path to Production”

- Modular monolith shell, auth, datasets, train/eval/register/deploy/monitor for tabular  
- Workflow Compiler v1 (compile → validate → execute)  
- Web + REST + CLI  
- HITL deploy gates, audit basics  

### ATLAS v2.0 — “Intelligent Platform”

- Knowledge Graph, Agent Memory, Meta Learning v1  
- Feature Store + Data Version Control  
- Visual Workflow Builder  
- Resource Scheduler with GPU quotas  
- Python + JS/TS SDKs  
- Plugin Marketplace beta  

### ATLAS v3.0 — “GenAI & Research”

- RAG Builder, Prompt Studio, LLM Evaluation  
- Research Mode  
- Distributed training (Ray/DeepSpeed/Accelerate) at scale  
- Synthetic Data Engine expansion  
- Workflow Marketplace  

### ATLAS Enterprise

- SSO/SCIM, hard tenancy, advanced RAI/compliance packs  
- Enterprise Analytics, cost/carbon controls  
- Chaos + formal SLOs  
- Air-gapped install options  

### ATLAS Cloud

- Managed control plane, billing, regional data residency  
- Hosted marketplace & shared (opt-in) Global Learning Memory  

### ATLAS Edge

- Slim inference runtime, offline sync, restricted Compiler feature set  

### ATLAS Research

- Paper-centric UX, reproducibility kits, academic export formats  

---

## 52. Cross-Reference Index (AAEP)

| Topic | Sections |
|-------|----------|
| AAEP definition | §30 |
| Five layers | §31 |
| Workflow Compiler | §32, §19, D017 |
| Knowledge Graph | §33, D018 |
| Agent Memory | §34, D019 |
| Meta Learning | §35, D020 |
| Planning / Scheduler | §36–§37, D021 |
| Distributed compute | §38, D024 |
| Feature Store / Data VCS | §39–§40, D022–D023 |
| Visual builder / collaboration | §41 |
| GenAI modules | §42 |
| Cost / Security / RAI | §43–§45, D025 |
| Analytics / Improvement | §46–§47, D029 |
| Marketplaces / SDKs | §48, D026–D028 |
| Chaos | §49 |
| Versions | §51, D030 |
| Agents & contracts | §14 |
| Locked decisions | §5 |

---

*End of source of truth. When in doubt, update this document before coding. AAEP sections extend—never silently erase—the foundation in §1–§29.*

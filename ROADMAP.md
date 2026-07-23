# ATLAS Roadmap

Living delivery plan. **`idea.md` remains the architectural source of truth.** Update both when phases or scope change.

**Last Updated:** 2026-07-23 (Phase 1 frozen as v0.1.0 Platform Foundation)

---

## Principles

1. Every phase ships a **working vertical**—not orphaned libraries.  
2. Prefer production patterns early (Docker, contracts, observability hooks).  
3. Extract microservices only when a bounded context has clear scale/isolation needs.  
4. Human-in-the-loop before production deploy is non-negotiable.  
5. Natural language is **compiled** to DAGs (Workflow Compiler)—never executed raw in production.  
6. AAEP modules land on the phase schedule below; see `idea.md` §30–§51 for architecture.

---

## Phase 0 — Project Foundation ✅

**Goal:** Repository, docs, structure, placeholders.

- [x] Git monorepo on `main`  
- [x] `idea.md`, `README.md`, `ARCHITECTURE.md`, `ROADMAP.md`, `CONTRIBUTING.md`  
- [x] MIT license, Code of Conduct, `.gitignore`, `.editorconfig`  
- [x] Full folder structure with module/agent placeholders  
- [x] Docker/K8s directory skeletons  

**Exit criteria:** Contributors can navigate the repo and understand the system from docs alone.

---

## Phase 1 — Tooling & Platform Skeleton ✅

**Goal:** Runnable empty platform shell.

**Release:** **v0.1.0 — ATLAS Platform Foundation** (2026-07-23)

- [x] `uv` Python workspace (`pyproject.toml`, packages)  
- [x] `pnpm`/`npm` workspace + Next.js app scaffold (production Next.js Docker image)  
- [x] FastAPI app health endpoints  
- [x] Docker Compose: api, worker, web, postgres, redis, minio, mlflow, prometheus, grafana  
- [x] OpenTelemetry hooks + structured logging + Prometheus metrics  
- [x] CI: lint + typecheck + unit tests + Docker build verification  
- [x] Helm chart templates for api/web/worker  
- [x] Local verification: Compose healthy, pytest/ruff/mypy/web lint+tsc pass  

**Exit criteria:** `docker compose up` brings up healthy services; web loads a shell UI; `/docs` and `/health` respond. **Met.**

**Completed:** 2026-07-23 — **frozen as v0.1.0**. Do not start Phase 2 until explicitly approved.

---

## Phase 2 — Authentication & Tenancy

- [ ] Users, organizations/tenants  
- [ ] JWT access/refresh  
- [ ] OAuth/OIDC provider hooks  
- [ ] RBAC roles & project membership  
- [ ] API keys  
- [ ] Audit log foundation  

**Exit criteria:** Authenticated multi-tenant API access with role checks.

---

## Phase 3 — Dataset Ingestion

- [ ] Project CRUD  
- [ ] Upload CSV / Excel / JSON / Parquet  
- [ ] MinIO-backed dataset versions  
- [ ] Connector interfaces (SQL, S3 stubs)  
- [ ] Dataset metadata catalog  

**Exit criteria:** User can upload a dataset and list versions in the UI.

---

## Phase 4 — Dataset Analysis

- [ ] Profiling pipeline (dtypes, nulls, distributions, correlations)  
- [ ] Target / problem-type heuristics  
- [ ] Leakage heuristics  
- [ ] Dataset Understanding Agent (structured + LLM summary)  
- [ ] EDA report artifacts  

**Exit criteria:** Upload → automatic profile + readable EDA summary.

---

## Phase 5 — Cleaning Pipeline

- [ ] Missing values, duplicates, outliers strategies  
- [ ] Encoding / scaling pipelines  
- [ ] Versioned preparation recipes  
- [ ] Data Cleaning Agent  

**Exit criteria:** Reproducible cleaned dataset artifact from a profiled source.

---

## Phase 6 — Feature Engineering

- [ ] Feature generation & selection baselines  
- [ ] Time-series / text feature hooks  
- [ ] Feature Engineering Agent  
- [ ] Feature store interface (stub)  

**Exit criteria:** Feature matrix version linked to experiment runs.

---

## Phase 7 — Training Engine

- [ ] sklearn / XGBoost / LightGBM / CatBoost adapters  
- [ ] Classification & regression first  
- [ ] Training Agent + worker execution  
- [ ] Reproducibility metadata (seeds, env, code hash)  

**Exit criteria:** Train a model from a prepared dataset via API/UI.

---

## Phase 8 — Hyperparameter Optimization

- [ ] Optuna integration  
- [ ] Early stopping  
- [ ] Search space templates by algorithm  
- [ ] HPO Agent  
- [ ] Ray Tune optional path  

**Exit criteria:** HPO study produces best-trial model with full trial history.

---

## Phase 9 — Experiment Tracking

- [ ] MLflow (or port) wired through `ExperimentTracker`  
- [ ] Params, metrics, artifacts, hardware info  
- [ ] Leaderboard UI  
- [ ] Compare runs  

**Exit criteria:** Every training/HPO run is queryable and comparable.

---

## Phase 10 — Explainability

- [ ] SHAP / LIME baselines  
- [ ] PDP / fairness stubs  
- [ ] Explainability Agent  
- [ ] Explainability views in UI  

**Exit criteria:** Approved model has an explanation report artifact.

---

## Phase 11 — Deployment

- [ ] FastAPI inference service generator  
- [ ] Docker image build for models  
- [ ] ONNX export where supported  
- [ ] K8s manifests / Helm values  
- [ ] Deployment Agent  
- [ ] OpenAPI for inference endpoints  

**Exit criteria:** One-click deploy of a registered model to a local/K8s endpoint.

---

## Phase 12 — Monitoring

- [ ] Latency / throughput / error metrics  
- [ ] Data/prediction drift detection  
- [ ] Alerting hooks  
- [ ] Monitoring Agent  
- [ ] Grafana dashboards  

**Exit criteria:** Live deployment shows health + drift signals.

---

## Phase 13 — Multi-Agent Orchestration

- [ ] Orchestrator planner (NL → DAG)  
- [ ] Budget/constraints (metrics gates, cost/time)  
- [ ] Agent message bus / durable workflow state  
- [ ] HITL approve/reject/schedule/canary  
- [ ] Assistant Agent chat  

**Exit criteria:** End-to-end NL prompt runs the lifecycle with approval gate.

---

## Phase 14 — Plugin Ecosystem

- [ ] Plugin manifest + entry points  
- [ ] Connectors, metrics, algorithms, notifications  
- [ ] Sandbox policy v1  
- [ ] Plugin manager UI  

**Exit criteria:** Third-party metric/connector installs without core code changes.

---

## Phase 15 — Federated Learning

- [ ] Flower (or chosen stack) prototype  
- [ ] Privacy-preserving training path  
- [ ] Docs + threat model  

**Exit criteria:** Demo federated job across ≥2 simulated clients.

---

## Phase 16 — Enterprise Features

- [ ] SSO hardening, SCIM (optional)  
- [ ] Fine-grained data policies  
- [ ] Cost optimization recommendations  
- [ ] Synthetic data (CTGAN/SMOTE paths)  
- [ ] Advanced multi-tenancy isolation  

**Exit criteria:** Enterprise checklist documented and partially demoable.

---

## Phase 17 — Production Hardening

- [ ] HA Postgres / Redis  
- [ ] Autoscaling workers/GPU pools  
- [ ] Backup/restore drills  
- [ ] SLOs, error budgets, chaos tests  
- [ ] Security review & penetration findings closed  

**Exit criteria:** Production runbook + SLO dashboards live.

---

## Phase 18 — Documentation & Public Launch

- [ ] Public docs site  
- [ ] Tutorials & reference architectures  
- [ ] Model card templates  
- [ ] IEEE-style system report  
- [ ] Launch checklist  

**Exit criteria:** External users can deploy and complete a sample workflow from docs alone.

---

## Parallel Workstreams (Anytime)

| Stream | Notes |
|--------|-------|
| NLP / CV / Multimodal | After tabular path is solid |
| Recommendation / Audio | Adapter-based expansion |
| Kafka event backbone | When fan-out exceeds Redis/Celery comfort |
| Marketplace | After plugins stabilize |
| Knowledge Graph / Agent Memory | Design with Phase 13; harden in v2.0 |
| Feature Store / Data VCS | Begin stubs after Phase 6; production in v2.0 |
| RAG / Prompt Studio / LLM Eval | After tabular + orchestration solid (v3.0) |
| Chaos Engineering | Staging continuous; prod game-days with approval |

---

## Product Versions & Editions (AAEP)

Phases 0–18 remain the engineering schedule. Versions package outcomes for stakeholders (`idea.md` §51):

| Version / Edition | Theme | Phase anchors |
|-------------------|--------|---------------|
| **ATLAS v1.0** | Governed path to production (tabular) | ~1–13 core path + Workflow Compiler v1 |
| **ATLAS v2.0** | Intelligence depth | Graph, Memory, Meta Learning, Feature Store, Data VCS, Visual Builder, SDKs |
| **ATLAS v3.0** | GenAI & Research | RAG, Prompt Studio, LLM Eval, Research Mode, distributed training scale |
| **ATLAS Enterprise** | Governance at scale | SSO/SCIM, RAI packs, analytics, chaos/SLOs, air-gap options |
| **ATLAS Cloud** | Managed SaaS | Control plane, billing, residency, hosted marketplace |
| **ATLAS Edge** | Constrained/on-prem inference | Slim serving + offline sync |
| **ATLAS Research** | Scientific reproducibility | Paper ingestion + reproducibility kits |

---

## Success Metrics (North Stars)

- Time from dataset upload to first evaluated model  
- % of runs fully reproducible from metadata  
- Deployment success rate & MTTR rollback  
- Drift detection lead time → retrain  
- Agent plan success rate (completed without manual repair)  
- % of production runs that passed Workflow Compiler validation  
- Meta Learning regret vs cold search (GPU-hours saved)  
- Governance gate effectiveness (blocked high-risk deploys)  

---

## Change Log

| Date | Change |
|------|--------|
| 2026-07-23 | Initial roadmap; Phase 0 marked complete |
| 2026-07-23 | AAEP expansion: versions/editions, parallel streams, extra north stars |
| 2026-07-23 | Phase 1 platform foundation marked complete |

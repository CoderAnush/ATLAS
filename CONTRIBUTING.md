# Contributing to ATLAS

Thank you for helping build ATLAS—an enterprise AI Operating System for Machine Learning.

## Golden Rule

**Read [`idea.md`](./idea.md) before any engineering work.**

- Treat it as the single source of truth.  
- Do not contradict locked design decisions.  
- If you must change architecture, stack, modules, or conventions, **update `idea.md` in the same PR**.  

Also read [`ARCHITECTURE.md`](./ARCHITECTURE.md) and [`ROADMAP.md`](./ROADMAP.md).

---

## Code of Conduct

Participation is governed by [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md).

---

## Development Principles

1. **Production-grade by default** — no throwaway hacks when a maintainable design fits.  
2. **Clean Architecture / SOLID / DDD** — respect bounded contexts under `services/`.  
3. **Contracts first** — agent and API schemas live in `packages/atlas-contracts`.  
4. **Observable** — log/trace/metric new paths; include `run_id` / `tenant_id` where applicable.  
5. **Tested** — unit tests for domain logic; integration tests at boundaries.  
6. **Secure** — never commit secrets; enforce tenant scoping on queries.  
7. **Docker/K8s aware** — assume containerized execution.  

---

## Repository Layout (Where to Put Things)

| Path | Put here |
|------|----------|
| `apps/api` | HTTP adapters, DI wiring |
| `apps/web` | Frontend |
| `apps/worker` | Async job runners |
| `services/<context>` | Domain + application for a bounded context |
| `agents/<name>` | Agent implementations |
| `packages/*` | Shared libraries |
| `plugins/*` | Installable extensions |
| `infrastructure/*` | Docker, Helm, K8s, monitoring |
| `tests/` | Cross-cutting integration/e2e |

---

## Tooling

| Area | Tool |
|------|------|
| Python | ≥3.11 (`uv`; 3.12+ preferred locally) |
| Node | Latest LTS; `pnpm` preferred, `npm` acceptable |
| Lint/format (Python) | Ruff + mypy |
| Lint/format (TS) | ESLint + Prettier |
| Tests | pytest (Phase 1 smoke); frontend unit runner later |
| Containers | Docker Compose locally |
| Shortcuts | `Makefile` (`make release-check`, `make compose-up`, …) |

Phase 1 scripts are finalized (`uv run`, `npm`/`pnpm`, `make`).

---

## Git Workflow

1. Branch from `main`: `feat/…`, `fix/…`, `docs/…`, `chore/…`  
2. Keep PRs focused and reviewable.  
3. Use [Conventional Commits](https://www.conventionalcommits.org/):  
   - `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`, `perf:`, `ci:`  
4. Update docs (`idea.md` / roadmap / architecture) when behavior or design changes.  
5. Do not force-push `main`.  

---

## Pull Request Checklist

- [ ] I read `idea.md` and this change aligns with it (or updates it).  
- [ ] Bounded context boundaries respected (no illicit cross-imports).  
- [ ] Public APIs documented (docstrings / OpenAPI).  
- [ ] Tests added or updated.  
- [ ] No secrets or credentials included.  
- [ ] Lint/typecheck/tests pass locally.  
- [ ] UI follows design principles in `idea.md` (when applicable).  

---

## Agent & ML Changes

- All agent I/O must use versioned contract models.  
- Record reproducibility metadata for training changes.  
- Prefer adapters behind ports (`ExperimentTracker`, `ObjectStorage`, `LLMClient`).  
- Budget-awareness (time/cost/tokens) for new agent steps.  

---

## Security Reports

Please do **not** open public issues for sensitive vulnerabilities. Contact the maintainers privately with reproduction details.

---

## License

By contributing, you agree that your contributions are licensed under the MIT License (`LICENSE`).

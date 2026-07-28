# atlas-modeling

ATLAS Phase 7 training engine (v0.7.0).

## Capabilities

- Deterministic training for classification and regression
- Algorithm adapter interface with pluggable estimators
- Async training jobs with HITL approve/reject gate
- Immutable model versions, lineage, metrics, and artifacts
- MinIO artifact persistence (model + report + config + pipeline)

## Package layout

```
domain/           enums and training invariants
application/      service, schemas, agent
infrastructure/   SQLAlchemy models, repository, engine
api/              FastAPI router under /v1/training
tests/            unit tests for training engine
```
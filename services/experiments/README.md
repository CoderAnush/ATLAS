# atlas-experiments

ATLAS Phase 9 experiment tracking platform (v0.9.0).

## Capabilities

- Experiment registry with runs, metrics, artifacts, tags, notes, and lineage
- Automatic experiment creation from training jobs and HPO studies
- Leaderboard and run comparison
- Reproducibility bundles (seed, environment, package versions, hashes)
- `ExperimentTracker` port with MLflow adapter (swap without API changes)

## Package layout

```
domain/           enums and invariants
application/      service, schemas, ports
infrastructure/   SQLAlchemy models, repository, MLflow tracker
api/              FastAPI router under /v1/experiments
tests/            unit tests for registry, leaderboard, comparison
```

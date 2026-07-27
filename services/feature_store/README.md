# atlas-feature-store

Intelligent Feature Engineering Platform (ATLAS Phase 6 / v0.6.0).

## Capabilities

- Feature generation (numeric interactions, polynomial/ratio/diff, log/sqrt/power, binning)
- Time / text / categorical / numeric transforms (encoding + scaling)
- Target-independent selection (variance, correlation); target-dependent methods stubbed until Phase 7
- Offline feature store with registry, versions, lineage, tags, statistics
- HITL approve / reject / edit → immutable feature matrix as new catalog dataset version
- Feature Engineering Agent (`agents/feature_engineering`)

## Package layout

```
domain/           enums & constants
application/      service, schemas, agent
infrastructure/   SQLAlchemy models, repository, engine
api/              FastAPI router under /v1/features
tests/            unit tests for the engine
```

## Notes

- Online feature serving is a placeholder (D022 offline-first in Phase 6).
- Target encoding, RFE, SHAP importance, UMAP, embeddings are stubs until training phases.
- Encoding/scaling deferred from Phase 5 live here.

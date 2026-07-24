# Profiling Service

Dataset understanding, automated EDA, quality scoring, leakage heuristics, and report artifacts.

## Layout

```text
domain/           enums, LLM port
application/      ProfilingService + schemas
infrastructure/   engine, loader, artifacts, models, repository
api/              /v1/profiling/*
```

Profiling runs asynchronously via Celery (`atlas.worker.profiling`). In `testing` env the API may run inline.

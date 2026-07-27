# Feature Engineering Agent

Production agent for ATLAS Phase 6 / v0.6.0. Proposes and executes feature pipelines with HITL approval before materializing feature matrices.

**Status:** Implemented (Phase 6)  
**Package:** `agents/feature_engineering` → delegates to `atlas_feature_store.application.agent`  
**Contracts:** `packages/atlas-contracts` (AgentRequest / AgentResponse)  
**See:** `idea.md` § AI Agents · `services/feature_store/README.md`

## Capabilities

- Numeric feature generation (interactions, polynomial/ratio/diff, log/sqrt/power, binning)
- Categorical encoding (one-hot, ordinal, frequency) and numeric scaling (standard, min-max, robust, quantile, power)
- Time-series hooks (calendar/part features, lags, rolling stats)
- Text hooks (TF-IDF, count, hashing vectorizers)
- Target-independent selection (variance threshold, correlation pruning)
- Quality scoring, pipeline JSON, report + recommendations
- Template NL summary (optional LLM provider port later)

## Entry points

| Surface | Function |
|---------|----------|
| Agent wrapper | `atlas_agent_feature_engineering.agent.run(request)` |
| Application | `atlas_feature_store.application.agent.run_feature_engineering_agent(df, profile, config)` |
| Worker | Celery `atlas.worker.features` → `FeatureStoreService.run_job` |

## Request shape

```python
{
  "dataframe": pd.DataFrame,  # or "records": [{...}, ...]
  "profile": {...},           # optional profiling JSON from Phase 4
  "config": {...},            # optional FE overrides
}
```

## Response shape

Returns `AgentResponse`-compatible dict: `status`, `agent`, `messages`, `artifacts` (pipeline, report, visualizations, recommendations), `metrics` (usefulness score), `next_hints`.

## Deferred to Phase 7+

- Target encoding, RFE, SHAP-based importance (require labeled target + training context)
- Online feature serving (offline store only in Phase 6; `online_enabled=False`)
- UMAP / deep embeddings beyond sklearn text vectorizers

"""Feature Engineering Agent — re-exports application agent."""

from __future__ import annotations

from typing import Any

from atlas_feature_store.application.agent import (
    AGENT_NAME,
    run_feature_engineering_agent,
    template_summary,
)

__all__ = ["AGENT_NAME", "run", "template_summary"]


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the Feature Engineering Agent.

    Expected request keys:
      - dataframe / records: tabular data
      - profile: optional profiling JSON
      - config: optional FE config
    """
    import pandas as pd

    profile = request.get("profile")
    config = request.get("config") or {}
    if "dataframe" in request:
        df = request["dataframe"]
    elif "records" in request:
        df = pd.DataFrame(request["records"])
    else:
        return {
            "status": "error",
            "agent": AGENT_NAME,
            "artifacts": [],
            "metrics": {},
            "messages": ["dataframe or records required"],
            "next_hints": [],
        }
    return run_feature_engineering_agent(df, profile=profile, config=config)

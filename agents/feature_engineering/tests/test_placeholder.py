"""Feature Engineering Agent tests."""

from __future__ import annotations

import pandas as pd
from atlas_agent_feature_engineering import AGENT_NAME, run


def test_agent_generates_pipeline() -> None:
    df = pd.DataFrame(
        {
            "age": [20, 30, 40, 25, 35],
            "income": [40_000, 55_000, 70_000, 45_000, 60_000],
            "city": ["a", "b", "a", "c", "b"],
        }
    )
    result = run({"records": df.to_dict(orient="records")})
    assert result["status"] in {"ok", "completed", "success"}
    assert result["agent"] == AGENT_NAME
    assert "pipeline" in result.get("artifacts", [{}])[0] or "pipeline" in result

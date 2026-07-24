"""Unit tests for profiling engine heuristics."""

from __future__ import annotations

import pandas as pd
from atlas_profiling.domain import ColumnKind, ProblemType
from atlas_profiling.infrastructure.engine import (
    detect_problem_type,
    detect_target,
    infer_column_kind,
    profile_dataframe,
)


def test_infer_kinds_and_target() -> None:
    df = pd.DataFrame(
        {
            "customer_id": range(100),
            "age": [20 + (i % 40) for i in range(100)],
            "salary": [30000 + i * 10 for i in range(100)],
            "survived": [i % 2 for i in range(100)],
        }
    )
    kinds = {c: infer_column_kind(df[c], c) for c in df.columns}
    assert kinds["customer_id"] is ColumnKind.ID
    assert kinds["survived"] in {ColumnKind.INTEGER, ColumnKind.BOOLEAN}
    target = detect_target(df, kinds)
    assert target["column"] == "survived"
    assert target["confidence"] > 0.5
    problem = detect_problem_type(df, target, kinds)
    assert problem is ProblemType.BINARY_CLASSIFICATION


def test_profile_dataframe_quality() -> None:
    df = pd.DataFrame(
        {
            "x": [1.0, 2.0, 3.0, None, 5.0],
            "y": ["a", "b", "a", "b", "a"],
            "label": [0, 1, 0, 1, 0],
        }
    )
    profile = profile_dataframe(df, file_size_bytes=128)
    assert profile["overview"]["rows"] == 5
    assert profile["quality"]["overall"] > 0
    assert "recommendations" in profile
    assert profile["leakage"]["count"] >= 0

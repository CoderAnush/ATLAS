"""Unit tests for preparation cleaning engine."""

from __future__ import annotations

import numpy as np
import pandas as pd
from atlas_preparation.infrastructure.engine import (
    apply_recipe,
    build_cleaning_plan,
    quality_snapshot,
)


def test_quality_snapshot_basic() -> None:
    df = pd.DataFrame({"a": [1, 2, None, 4], "b": [1, 1, 1, 1]})
    snap = quality_snapshot(df)
    assert snap["rows"] == 4
    assert snap["columns"] == 2
    assert snap["missing_cells"] == 1
    assert snap["quality_overall"] > 0


def test_build_plan_and_apply() -> None:
    df = pd.DataFrame(
        {
            "id": [1, 2, 3, 3],
            "age": [20.0, np.nan, 40.0, 40.0],
            "country": [" US ", "us", "UK", "uk"],
            "empty": [None, None, None, None],
        }
    )
    plan = build_cleaning_plan(df, profile=None, strategies={"drop_duplicates": True})
    assert plan["steps"]
    cleaned = apply_recipe(df, plan["steps"])
    assert cleaned.shape[0] <= df.shape[0]
    assert plan["after"]["quality_overall"] >= plan["before"]["quality_overall"] - 1e-6


def test_impute_median() -> None:
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0]})
    out = apply_recipe(
        df,
        [
            {
                "order": 1,
                "kind": "impute_median",
                "column": "x",
                "params": {},
                "reason": "",
                "expected_impact": "",
            }
        ],
    )
    assert not out["x"].isna().any()
    assert float(out["x"].iloc[1]) == 2.0


def test_missing_strategy_ffill_and_knn() -> None:
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]})
    plan = build_cleaning_plan(df, strategies={"missing": "ffill", "drop_id_columns": False})
    kinds = {s["kind"] for s in plan["steps"]}
    assert "impute_ffill" in kinds
    plan_knn = build_cleaning_plan(df, strategies={"missing": "knn", "drop_id_columns": False})
    assert any(s["kind"] == "impute_knn" for s in plan_knn["steps"])


def test_outlier_dbscan_and_cap() -> None:
    values = [10.0] * 20 + [1000.0]
    df = pd.DataFrame({"x": values})
    plan = build_cleaning_plan(
        df,
        strategies={
            "outlier_method": "dbscan",
            "outlier_action": "cap",
            "drop_id_columns": False,
            "drop_duplicates": False,
            "drop_near_duplicates": False,
        },
    )
    cleaned = apply_recipe(df, plan["steps"])
    assert cleaned["x"].max() < 1000 or any(s["kind"].startswith("outlier_") for s in plan["steps"])


def test_text_unicode_and_categorical_merge() -> None:
    df = pd.DataFrame(
        {
            "country": ["USA", "usa", "U.S.A", "Canada"],
            "notes": ["Hello\u00a0World", "  Foo  ", "Bar", "Baz"],
        }
    )
    plan = build_cleaning_plan(
        df,
        profile={
            "columns": [
                {"name": "country", "kind": "categorical"},
                {"name": "notes", "kind": "text"},
            ]
        },
        strategies={"drop_id_columns": False, "drop_duplicates": False, "merge_categories": True},
    )
    kinds = {s["kind"] for s in plan["steps"]}
    assert "text_normalize" in kinds or "categorical_normalize" in kinds
    cleaned = apply_recipe(df, plan["steps"])
    assert cleaned.shape[0] == df.shape[0]

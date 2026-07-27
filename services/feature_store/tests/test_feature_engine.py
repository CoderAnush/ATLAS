"""Unit tests for feature engineering engine."""

from __future__ import annotations

import pandas as pd
from atlas_feature_store.infrastructure.engine import (
    apply_pipeline,
    build_feature_pipeline,
    feature_quality_scores,
    run_feature_engineering,
    validate_features,
)


def _sample_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [1, 2, 3, 4, 5],
            "age": [25.0, 30.0, 35.0, 40.0, 45.0],
            "score": [80.0, 90.0, 85.0, 95.0, 88.0],
            "country": ["US", "UK", "US", "CA", "UK"],
            "created_at": pd.to_datetime(
                [
                    "2024-01-15 10:00:00",
                    "2024-02-20 14:30:00",
                    "2024-03-10 09:15:00",
                    "2024-04-05 16:45:00",
                    "2024-05-12 11:00:00",
                ]
            ),
            "description": [
                "hello world from atlas",
                "feature engineering test row two",
                "short text",
                "another sample description here",
                "final row with words",
            ],
            "target_label": [0, 1, 0, 1, 0],
        }
    )


def test_feature_quality_scores() -> None:
    df = _sample_df()
    scores = feature_quality_scores(df["age"])
    assert 0 <= scores["uniqueness"] <= 1
    assert 0 <= scores["variance"] <= 1
    assert scores["missing_pct"] == 0.0
    assert scores["overall_score"] > 0


def test_validate_features() -> None:
    df = _sample_df()
    result = validate_features(df)
    assert "issues" in result
    assert "drop_candidates" in result
    assert isinstance(result["issues"], list)


def test_build_feature_pipeline() -> None:
    df = _sample_df()
    pipeline = build_feature_pipeline(df, profile=None, config={"target": "target_label"})
    assert pipeline["steps"]
    assert pipeline["version"]
    assert "numeric" in pipeline["column_types"]


def test_apply_pipeline_expands_columns() -> None:
    df = _sample_df()
    pipeline = build_feature_pipeline(df, config={"target": "target_label"})
    matrix, report = apply_pipeline(df, pipeline["steps"])
    assert len(matrix.columns) > len(df.columns)
    assert report["summary"]["final_features"] >= len(df.columns)
    assert report["applied_steps"]


def test_run_feature_engineering_end_to_end() -> None:
    df = _sample_df()
    result = run_feature_engineering(df, profile=None, config={"target": "target_label"})
    assert result["pipeline"]["steps"]
    assert result["matrix_shape"][1] > df.shape[1]
    assert result["summary"]["features_created"] >= 0
    assert "visualizations" in result
    assert "recommendations" in result

from __future__ import annotations

import pandas as pd
from atlas_modeling.infrastructure.engine import run_training


def test_run_training_regression_metrics() -> None:
    df = pd.DataFrame(
        {
            "x1": [1, 2, 3, 4, 5, 6, 7, 8],
            "x2": [2, 1, 3, 2, 4, 3, 5, 4],
            "target": [3, 3, 6, 6, 9, 9, 12, 12],
        }
    )
    out = run_training(
        df,
        target_column="target",
        problem_type_value="regression",
        config={"algorithm": "linear_regression", "validation_size": 0.25, "random_seed": 7},
    )
    assert "mae" in out.metrics
    assert "r2" in out.metrics
    assert out.training_seconds >= 0
    assert out.model_bytes

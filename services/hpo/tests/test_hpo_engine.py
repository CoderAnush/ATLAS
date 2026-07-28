from __future__ import annotations

import pandas as pd
from atlas_hpo.infrastructure.engine import build_search_space, run_optimization


def test_build_search_space_for_random_forest() -> None:
    search_space = build_search_space("random_forest", "binary_classification")

    assert "n_estimators" in search_space
    assert search_space["bootstrap"]["kind"] == "bool"


def test_run_optimization_returns_best_trial() -> None:
    df = pd.DataFrame(
        {
            "feature_a": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
            "feature_b": [1, 1, 0, 0, 1, 1, 0, 0, 1, 1],
            "target": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )

    result = run_optimization(
        df,
        target_column="target",
        problem_type="binary_classification",
        algorithm="decision_tree",
        optimizer="random",
        metric_objective="accuracy",
        budget={"max_trials": 3, "parallel_workers": 1},
        base_config={"random_seed": 42},
    )

    assert result.best_value is not None
    assert len(result.trials) >= 1
    assert result.summary["completed_trials"] >= 1

from atlas_agent_hpo.agent import run


def test_placeholder_run():
    result = run(
        {
            "run_id": "00000000-0000-0000-0000-000000000000",
            "algorithm": "random_forest",
            "problem_type": "binary_classification",
        }
    )
    assert result["status"] == "ready"
    assert result["agent"] == "hyperparameter_optimization"
    assert "search_space" in result
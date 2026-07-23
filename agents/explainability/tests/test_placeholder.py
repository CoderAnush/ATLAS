from atlas_agent_explainability.agent import run


def test_placeholder_run():
    result = run({"run_id": "00000000-0000-0000-0000-000000000000"})
    assert result["status"] == "not_implemented"
    assert result["agent"] == "explainability"
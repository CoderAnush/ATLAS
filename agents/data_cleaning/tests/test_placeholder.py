"""Data Cleaning Agent package tests."""

from __future__ import annotations

import pandas as pd
from atlas_agent_data_cleaning import AGENT_NAME, run


def test_agent_requires_dataframe() -> None:
    response = run(None)
    assert response.status == "not_implemented"
    assert AGENT_NAME == "data_cleaning"


def test_agent_produces_recipe() -> None:
    df = pd.DataFrame({"id": [1, 2, 2], "age": [20.0, None, 40.0], "country": [" US", "us", "UK"]})
    response = run(None, dataframe=df)
    assert response.status == "ok"
    assert "recipe" in response.metadata
    assert response.metadata["recipe"]["steps"]

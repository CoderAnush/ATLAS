"""Data Cleaning Agent module.

Thin re-export of the preparation-package agent for the agents/ tree layout.
"""

from __future__ import annotations

from typing import Any

from atlas_contracts.agents import AgentRequest, AgentResponse
from atlas_preparation.application.agent import (
    AGENT_NAME,
    run_data_cleaning_agent,
    template_summary,
)

__all__ = ["AGENT_NAME", "run", "template_summary"]


def run(
    request: AgentRequest | dict[str, Any] | None = None,
    *,
    dataframe: Any | None = None,
    profile: dict[str, Any] | None = None,
    strategies: dict[str, Any] | None = None,
) -> AgentResponse:
    """Execute the data cleaning agent."""
    return run_data_cleaning_agent(
        request, dataframe=dataframe, profile=profile, strategies=strategies
    )

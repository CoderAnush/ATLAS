"""Dataset Understanding Agent — first production ATLAS agent."""

from __future__ import annotations

from typing import Any

from atlas_contracts.agents import AgentRequest, AgentResponse
from atlas_profiling.application.agent import (
    AGENT_NAME,
    run_dataset_understanding,
    template_summary,
)

__all__ = ["AGENT_NAME", "run", "template_summary"]


def run(
    request: AgentRequest | dict[str, Any] | None = None,
    *,
    dataframe: Any | None = None,
    file_size_bytes: int | None = None,
    llm: Any | None = None,
) -> AgentResponse:
    return run_dataset_understanding(
        request, dataframe=dataframe, file_size_bytes=file_size_bytes, llm=llm
    )

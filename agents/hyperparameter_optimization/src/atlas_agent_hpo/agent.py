"""Hyperparameter Optimization Agent wrapper."""

from __future__ import annotations

from typing import Any

from atlas_hpo.application.agent import run as run_hpo_agent

AGENT_NAME = "hyperparameter_optimization"


def run(request: dict[str, Any]) -> dict[str, Any]:
    """Execute the HPO agent through the service entrypoint."""
    response = run_hpo_agent(request)
    response.setdefault("agent", AGENT_NAME)
    return response

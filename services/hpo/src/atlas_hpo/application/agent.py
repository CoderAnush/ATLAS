"""Application-facing HPO agent entrypoint."""

from __future__ import annotations

from typing import Any

from atlas_hpo.infrastructure.engine import build_search_space


def run(request: dict[str, Any]) -> dict[str, Any]:
    algorithm = str(request.get("algorithm") or "")
    problem_type = str(request.get("problem_type") or "")
    return {
        "status": "ready",
        "agent": "hyperparameter_optimization",
        "artifacts": [],
        "metrics": {},
        "messages": ["HPO agent prepared search space and optimization request."],
        "next_hints": [],
        "search_space": build_search_space(algorithm, problem_type),
        "echo": request,
    }

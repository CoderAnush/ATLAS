"""Training Agent entrypoint."""

from __future__ import annotations

from typing import Any

import pandas as pd

from atlas_modeling.infrastructure.engine import run_training

AGENT_NAME = "training"


def template_summary(report: dict[str, Any]) -> str:
    metrics = report.get("metrics") or {}
    alg = report.get("algorithm", "unknown")
    problem = report.get("problem_type", "unknown")
    split = report.get("split") or {}
    return (
        f"Trained {alg} for {problem}. "
        f"Validation rows: {split.get('validation_rows', 0)}. "
        f"Metrics keys: {', '.join(sorted(metrics.keys()))}."
    )


def run_training_agent(request: dict[str, Any]) -> dict[str, Any]:
    records = request.get("records")
    if not isinstance(records, list) or not records:
        return {
            "status": "error",
            "agent": AGENT_NAME,
            "messages": ["records are required"],
            "metrics": {},
            "artifacts": [],
            "next_hints": [],
        }
    target_column = str(request.get("target_column") or "")
    problem_type = str(request.get("problem_type") or "")
    if not target_column or not problem_type:
        return {
            "status": "error",
            "agent": AGENT_NAME,
            "messages": ["target_column and problem_type are required"],
            "metrics": {},
            "artifacts": [],
            "next_hints": [],
        }
    df = pd.DataFrame(records)
    outcome = run_training(
        df,
        target_column=target_column,
        problem_type_value=problem_type,
        config=request.get("config") or {},
    )
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "messages": [template_summary(outcome.report)],
        "metrics": outcome.metrics,
        "artifacts": [{"report": outcome.report}],
        "next_hints": ["approve model registration", "export model artifacts"],
    }


__all__ = ["AGENT_NAME", "run_training_agent", "template_summary"]

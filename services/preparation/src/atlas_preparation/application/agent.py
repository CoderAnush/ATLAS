"""Data Cleaning Agent entrypoint (lives in preparation package)."""

from __future__ import annotations

from typing import Any

from atlas_contracts.agents import AgentRequest, AgentResponse

from atlas_preparation.infrastructure.engine import (
    apply_recipe,
    quality_snapshot,
    run_data_cleaning,
)

AGENT_NAME = "data_cleaning"


def template_summary(result: dict[str, Any]) -> str:
    """Generate a human-readable summary from cleaning results."""
    before = result.get("before", {})
    after = result.get("after", {})
    improvement = result.get("improvement", {})
    steps = result.get("recipe", {}).get("steps", [])

    lines = [
        f"Proposed {len(steps)} cleaning step(s) for this dataset.",
        f"Quality score: {before.get('quality_overall', 0):.1f} → {after.get('quality_overall', 0):.1f} "
        f"(Δ {improvement.get('quality_delta', 0):+.2f}).",
    ]

    if before.get("missing_pct", 0) > 0:
        lines.append(
            f"Missing values: {before.get('missing_pct', 0):.2f}% → {after.get('missing_pct', 0):.2f}%."
        )

    if before.get("duplicate_pct", 0) > 0:
        lines.append(
            f"Duplicates: {before.get('duplicate_pct', 0):.2f}% → {after.get('duplicate_pct', 0):.2f}%."
        )

    step_kinds = [s.get("kind", "unknown") for s in steps[:5]]
    if step_kinds:
        lines.append(f"Key transformations: {', '.join(step_kinds)}.")

    if len(steps) > 5:
        lines.append(f"Plus {len(steps) - 5} additional steps.")

    lines.append("Review the proposed recipe and approve or reject changes.")

    return "\n\n".join(lines)


def run_data_cleaning_agent(
    request: AgentRequest | dict[str, Any] | None = None,
    *,
    dataframe: Any | None = None,
    profile: dict[str, Any] | None = None,
    strategies: dict[str, Any] | None = None,
) -> AgentResponse:
    """Execute data cleaning analysis and produce a cleaning plan.

    This agent analyzes a dataframe, optionally using an existing profile,
    and produces a cleaning recipe with before/after quality metrics.
    The recipe awaits human approval before being applied.
    """
    if dataframe is None:
        return AgentResponse(
            status="not_implemented",
            messages=["Pass a loaded dataframe to run data cleaning analysis"],
            artifacts=[],
            metadata={"agent": AGENT_NAME},
        )

    result = run_data_cleaning(dataframe, profile, strategies=strategies)
    summary = template_summary(result)

    result["summary"] = summary

    _ = request

    return AgentResponse(
        status="ok",
        messages=[summary],
        artifacts=["recipe.json", "report.json"],
        metadata={
            "agent": AGENT_NAME,
            "recipe": result["recipe"],
            "plan": result["plan"],
            "before": result["before"],
            "after": result["after"],
            "improvement": result["improvement"],
            "summary": summary,
            "graph": result["graph"],
        },
    )


__all__ = [
    "AGENT_NAME",
    "apply_recipe",
    "quality_snapshot",
    "run_data_cleaning",
    "run_data_cleaning_agent",
    "template_summary",
]

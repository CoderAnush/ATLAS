"""Feature Engineering Agent entrypoint (lives in feature_store package)."""

from __future__ import annotations

from typing import Any

from atlas_feature_store.infrastructure.engine import run_feature_engineering

AGENT_NAME = "feature_engineering"


def template_summary(result: dict[str, Any]) -> str:
    """Generate a human-readable summary from feature engineering results."""
    summary = result.get("summary", {})
    if isinstance(summary, str):
        return summary
    recommendations = result.get("recommendations", [])

    input_shape = summary.get("input_shape", (0, 0))
    output_shape = summary.get("output_shape", result.get("matrix_shape", (0, 0)))
    features_created = summary.get("features_created", 0)
    usefulness_score = float(summary.get("usefulness_score", 0.0) or 0.0)
    quality_issues = summary.get("quality_issues", 0)

    lines = [
        f"Generated {features_created} new features from {input_shape[1] if len(input_shape) > 1 else 0} original columns.",
        f"Final feature matrix: {output_shape[0]} rows × {output_shape[1]} columns.",
        f"Usefulness score: {usefulness_score:.1f}/100.",
    ]

    if quality_issues > 0:
        lines.append(f"Detected {quality_issues} quality issue(s) that were addressed.")

    if recommendations:
        lines.append(f"Generated {len(recommendations)} recommendation(s).")

    lines.append("Review the proposed feature pipeline and approve or reject changes.")
    return " ".join(lines)


def run_feature_engineering_agent(
    df: Any,
    profile: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute feature engineering analysis and produce a feature pipeline."""
    result = run_feature_engineering(df, profile, config)
    text = template_summary(result)
    return {
        "status": "ok",
        "agent": AGENT_NAME,
        "messages": [text],
        "artifacts": [
            {
                "pipeline": result["pipeline"],
                "report": result["report"],
                "visualizations": result.get("visualizations", {}),
                "recommendations": result.get("recommendations", []),
                "summary": result.get("summary"),
                "preview_columns": result.get("preview_columns"),
                "matrix_shape": result.get("matrix_shape"),
            }
        ],
        "metrics": {
            "usefulness_score": (result.get("summary") or {}).get("usefulness_score", 0)
            if isinstance(result.get("summary"), dict)
            else 0
        },
        "next_hints": ["approve feature pipeline", "export feature matrix"],
        "pipeline": result["pipeline"],
        "report": result["report"],
    }


__all__ = [
    "AGENT_NAME",
    "run_feature_engineering_agent",
    "template_summary",
]

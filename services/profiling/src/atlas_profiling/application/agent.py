"""Dataset Understanding Agent entrypoint (lives in profiling package)."""

from __future__ import annotations

from typing import Any

from atlas_contracts.agents import AgentRequest, AgentResponse

from atlas_profiling.domain.llm import LLMProvider, StubLLMProvider
from atlas_profiling.infrastructure.engine import profile_dataframe

AGENT_NAME = "dataset_understanding"


def template_summary(profile: dict[str, Any]) -> str:
    ov = profile["overview"]
    q = profile["quality"]
    target = profile["target"]
    leakage = profile["leakage"]
    lines = [
        f"This dataset contains {ov['rows']:,} rows and {ov['columns']} columns.",
        f"The data appears suitable for {profile['problem_type'].replace('_', ' ')}.",
        f"There are {q['missing_pct']}% missing values (quality {q['overall']}/100, health {q['health']}).",
    ]
    if target.get("column"):
        lines.append(
            f"Inferred target column `{target['column']}` with confidence {float(target['confidence']):.0%}."
        )
    else:
        lines.append("No obvious target column was detected automatically.")
    id_cols = [c["name"] for c in profile["columns"] if c.get("kind") == "id"]
    if id_cols:
        lines.append(f"`{id_cols[0]}` should probably be removed from features.")
    outlier_cols = [
        c["name"]
        for c in profile["columns"]
        if (c.get("outliers") or {}).get("iqr_count", 0) > max(10, 0.01 * ov["rows"])
    ]
    if outlier_cols:
        lines.append(f"`{outlier_cols[0]}` contains notable outliers.")
    if leakage.get("count"):
        lines.append(f"{leakage['count']} potential leakage signal(s) were detected.")
    else:
        lines.append("No obvious leakage was detected.")
    lines.append("Recommended next step: Proceed to Data Cleaning.")
    return "\n\n".join(lines)


def run_dataset_understanding(
    request: AgentRequest | dict[str, Any] | None = None,
    *,
    dataframe: Any | None = None,
    file_size_bytes: int | None = None,
    llm: LLMProvider | None = None,
) -> AgentResponse:
    if dataframe is None:
        return AgentResponse(
            status="not_implemented",
            messages=["Pass a loaded dataframe to run profiling"],
            artifacts=[],
            metadata={"agent": AGENT_NAME},
        )
    profile = profile_dataframe(dataframe, file_size_bytes=file_size_bytes)
    summary = template_summary(profile)
    provider = llm or StubLLMProvider()
    try:
        polished = provider.summarize(
            "Polish this dataset EDA summary for an ML engineer:\n" + summary
        )
        if polished.strip():
            summary = polished.strip()
            profile["summary_source"] = "llm"
        else:
            profile["summary_source"] = "template"
    except Exception:  # noqa: BLE001
        profile["summary_source"] = "template"
    profile["summary"] = summary
    _ = request
    return AgentResponse(
        status="ok",
        messages=[summary],
        artifacts=["profile.json"],
        metadata={"agent": AGENT_NAME, "profile": profile},
    )

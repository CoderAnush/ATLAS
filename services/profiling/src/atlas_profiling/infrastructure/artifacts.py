"""Report + visualization artifact builders."""

from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import plotly.express as px
import plotly.graph_objects as go
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def build_markdown(profile: dict[str, Any], summary: str) -> str:
    ov = profile["overview"]
    q = profile["quality"]
    lines = [
        "# Dataset Understanding Report",
        "",
        summary,
        "",
        "## Overview",
        f"- Rows: {ov['rows']}",
        f"- Columns: {ov['columns']}",
        f"- Memory: {ov['memory_bytes']} bytes",
        f"- Duplicates: {ov['duplicate_rows']}",
        "",
        "## Quality",
        f"- Overall: {q['overall']} ({q['health']})",
        f"- Completeness: {q['completeness']}",
        f"- Consistency: {q['consistency']}",
        f"- Validity: {q['validity']}",
        f"- Uniqueness: {q['uniqueness']}",
        "",
        "## Target & Problem",
        f"- Target: {profile['target'].get('column')} (confidence {profile['target'].get('confidence')})",
        f"- Problem type: {profile['problem_type']}",
        "",
        "## Leakage findings",
    ]
    for f in profile["leakage"].get("findings", []):
        lines.append(f"- [{f['severity']}] {f['type']}: `{f['column']}` — {f['detail']}")
    if not profile["leakage"].get("findings"):
        lines.append("- None detected")
    lines.extend(["", "## Recommendations"])
    for tip in profile.get("recommendations", []):
        lines.append(f"- {tip}")
    lines.extend(["", "## Columns"])
    for col in profile["columns"]:
        lines.append(
            f"- `{col['name']}` ({col['kind']}): missing={col['missing_pct']}%, unique={col['unique']}"
        )
    return "\n".join(lines) + "\n"


def build_html(profile: dict[str, Any], summary: str, md: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ATLAS Dataset Profile</title>
<style>
body{{font-family:Segoe UI,sans-serif;margin:2rem;background:#0f1419;color:#e7ecf1}}
pre{{white-space:pre-wrap;background:#1a222c;padding:1rem;border-radius:8px}}
h1,h2{{color:#7dd3fc}}
</style></head><body>
<h1>ATLAS Dataset Understanding</h1>
<p>{summary.replace(chr(10), "<br/>")}</p>
<pre>{md}</pre>
</body></html>
"""


def build_pdf(summary: str, profile: dict[str, Any]) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    width, height = letter
    y = height - 50
    c.setFont("Helvetica-Bold", 14)
    c.drawString(40, y, "ATLAS Dataset Understanding Report")
    y -= 24
    c.setFont("Helvetica", 10)
    for line in summary.splitlines():
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)
        c.drawString(40, y, line[:100])
        y -= 14
    y -= 10
    c.drawString(
        40, y, f"Quality overall: {profile['quality']['overall']} ({profile['quality']['health']})"
    )
    y -= 14
    c.drawString(40, y, f"Problem: {profile['problem_type']}")
    c.showPage()
    c.save()
    return buf.getvalue()


def build_visualizations(df_sample: Any, profile: dict[str, Any]) -> dict[str, Any]:
    """Return Plotly figure JSON payloads (no browser JS required to store)."""
    figs: dict[str, Any] = {}
    missing_pct = [
        {"column": c["name"], "missing_pct": c["missing_pct"]} for c in profile["columns"]
    ]
    if missing_pct:
        fig = px.bar(missing_pct, x="column", y="missing_pct", title="Missing values %")
        figs["missing_bar"] = json.loads(fig.to_json())

    corr = profile.get("correlations", {})
    cols = corr.get("columns") or []
    matrix = corr.get("pearson") or []
    if cols and matrix:
        fig = go.Figure(data=go.Heatmap(z=matrix, x=cols, y=cols, colorscale="RdBu", zmid=0))
        fig.update_layout(title="Pearson correlation")
        figs["correlation_heatmap"] = json.loads(fig.to_json())

    # distributions for up to 6 numeric columns
    for col in profile["columns"]:
        if col.get("kind") not in {"integer", "float"}:
            continue
        if "distributions" not in figs:
            figs["distributions"] = []
        if len(figs["distributions"]) >= 6:
            break
        stats = col.get("statistics") or {}
        hist = stats.get("histogram") or {}
        if not hist.get("counts"):
            continue
        edges = hist.get("edges") or []
        centers = [((edges[i] or 0) + (edges[i + 1] or 0)) / 2 for i in range(len(edges) - 1)]
        fig = go.Figure(data=[go.Bar(x=centers, y=hist["counts"])])
        fig.update_layout(title=f"Histogram: {col['name']}")
        figs["distributions"].append({"column": col["name"], "figure": json.loads(fig.to_json())})

    # class imbalance if target categorical-ish
    target = profile.get("target", {}).get("column")
    if target and target in getattr(df_sample, "columns", []):
        vc = df_sample[target].astype(str).value_counts().head(20)
        fig = px.pie(
            names=vc.index.astype(str), values=vc.values, title=f"Target imbalance: {target}"
        )
        figs["class_imbalance"] = json.loads(fig.to_json())
        fig2 = px.bar(x=vc.index.astype(str), y=vc.values, title=f"Value counts: {target}")
        figs["value_counts"] = json.loads(fig2.to_json())

    # boxplot for first numeric
    for col in profile["columns"]:
        if col.get("kind") in {"integer", "float"} and col["name"] in getattr(
            df_sample, "columns", []
        ):
            fig = px.box(df_sample, y=col["name"], title=f"Boxplot: {col['name']}")
            figs["boxplot"] = json.loads(fig.to_json())
            break

    # missing heatmap sample
    miss = profile.get("missing", {})
    if miss.get("matrix"):
        fig = go.Figure(
            data=go.Heatmap(
                z=miss["matrix"],
                x=miss.get("columns"),
                colorscale="Greys",
            )
        )
        fig.update_layout(title="Missingness pattern (sample rows)")
        figs["missing_heatmap"] = json.loads(fig.to_json())

    return figs

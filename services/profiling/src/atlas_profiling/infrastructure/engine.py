"""Deterministic dataset profiling engine (no training, no cleaning)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.ensemble import IsolationForest

from atlas_profiling.domain import (
    ID_NAME_HINTS,
    TARGET_NAME_HINTS,
    ColumnKind,
    DatasetHealth,
    ProblemType,
)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            return None
        out = float(value)
        if math.isnan(out) or math.isinf(out):
            return None
        return out
    except Exception:  # noqa: BLE001
        return None


def infer_column_kind(series: pd.Series, name: str) -> ColumnKind:
    non_null = series.dropna()
    nunique = int(non_null.nunique()) if len(non_null) else 0
    if nunique <= 1:
        return ColumnKind.CONSTANT
    lower = name.lower().strip()
    if lower in ID_NAME_HINTS or lower.endswith("_id") or lower.endswith("id"):
        if nunique >= max(10, int(0.9 * len(non_null))):
            return ColumnKind.ID
    if pd.api.types.is_bool_dtype(series) or set(non_null.astype(str).str.lower().unique()) <= {
        "true",
        "false",
        "0",
        "1",
        "yes",
        "no",
    }:
        if nunique <= 2:
            return ColumnKind.BOOLEAN
    if pd.api.types.is_datetime64_any_dtype(series):
        return ColumnKind.DATETIME
    if pd.api.types.is_numeric_dtype(series):
        if pd.api.types.is_integer_dtype(series):
            return ColumnKind.INTEGER
        return ColumnKind.FLOAT
    # try datetime parse
    if non_null.dtype == object:
        sample = non_null.head(50).astype(str)
        parsed = pd.to_datetime(sample, errors="coerce", utc=True)
        if parsed.notna().mean() > 0.8:
            return ColumnKind.DATETIME
        avg_len = sample.str.len().mean() if len(sample) else 0
        if nunique <= min(50, max(2, int(0.05 * len(non_null)))):
            return ColumnKind.CATEGORICAL
        if avg_len > 40 or nunique > 0.5 * len(non_null):
            return ColumnKind.TEXT
        return ColumnKind.CATEGORICAL
    return ColumnKind.MIXED


def profile_numeric(series: pd.Series) -> dict[str, Any]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if clean.empty:
        return {}
    desc = clean.describe(percentiles=[0.25, 0.5, 0.75, 0.9, 0.95, 0.99])
    q1, q3 = float(desc["25%"]), float(desc["75%"])
    iqr = q3 - q1
    hist_counts, hist_edges = np.histogram(
        clean.to_numpy(), bins=min(20, max(5, int(np.sqrt(len(clean)))))
    )
    return {
        "count": int(len(clean)),
        "mean": _safe_float(desc["mean"]),
        "median": _safe_float(desc["50%"]),
        "mode": _safe_float(clean.mode().iloc[0]) if len(clean.mode()) else None,
        "variance": _safe_float(clean.var()),
        "std": _safe_float(desc["std"]),
        "min": _safe_float(desc["min"]),
        "max": _safe_float(desc["max"]),
        "q1": _safe_float(q1),
        "q3": _safe_float(q3),
        "iqr": _safe_float(iqr),
        "skewness": _safe_float(stats.skew(clean)),
        "kurtosis": _safe_float(stats.kurtosis(clean)),
        "percentiles": {
            "p90": _safe_float(desc["90%"]),
            "p95": _safe_float(desc["95%"]),
            "p99": _safe_float(desc["99%"]),
        },
        "histogram": {
            "counts": [int(c) for c in hist_counts.tolist()],
            "edges": [_safe_float(e) for e in hist_edges.tolist()],
        },
    }


def profile_categorical(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna().astype(str)
    vc = non_null.value_counts()
    top = vc.head(20)
    rare = vc[vc / max(len(non_null), 1) < 0.01]
    return {
        "unique_count": int(vc.shape[0]),
        "top_categories": [{"value": k, "count": int(v)} for k, v in top.items()],
        "rare_category_count": int(rare.shape[0]),
        "missing": int(series.isna().sum()),
    }


def profile_text(series: pd.Series) -> dict[str, Any]:
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return {}
    lengths = non_null.str.len()
    tokens: set[str] = set()
    for text in non_null.head(2000):
        tokens.update(w.lower() for w in text.split() if w)
    # lightweight language heuristic
    ascii_ratio = (
        non_null.head(500).apply(lambda s: sum(ord(c) < 128 for c in s) / max(len(s), 1)).mean()
    )
    language = "en" if ascii_ratio > 0.85 else "unknown"
    return {
        "avg_length": _safe_float(lengths.mean()),
        "min_length": int(lengths.min()),
        "max_length": int(lengths.max()),
        "vocabulary_size": int(len(tokens)),
        "language": language,
    }


def profile_datetime(series: pd.Series) -> dict[str, Any]:
    dt = pd.to_datetime(series, errors="coerce", utc=True)
    clean = dt.dropna()
    if clean.empty:
        return {"missing": int(series.isna().sum())}
    sorted_dt = clean.sort_values()
    deltas = sorted_dt.diff().dropna().dt.total_seconds()
    median_gap = _safe_float(deltas.median()) if len(deltas) else None
    granularity = "unknown"
    if median_gap is not None:
        if median_gap < 120:
            granularity = "seconds"
        elif median_gap < 7200:
            granularity = "minutes"
        elif median_gap < 172800:
            granularity = "hours"
        elif median_gap < 1_209_600:
            granularity = "days"
        else:
            granularity = "weeks_or_more"
    return {
        "earliest": sorted_dt.iloc[0].isoformat(),
        "latest": sorted_dt.iloc[-1].isoformat(),
        "missing": int(dt.isna().sum()),
        "median_interval_seconds": median_gap,
        "granularity": granularity,
    }


def outlier_report(series: pd.Series) -> dict[str, Any]:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) < 10:
        return {
            "iqr_count": 0,
            "zscore_count": 0,
            "modified_z_count": 0,
            "isolation_forest_count": 0,
        }
    q1, q3 = clean.quantile(0.25), clean.quantile(0.75)
    iqr = q3 - q1
    iqr_mask = (clean < q1 - 1.5 * iqr) | (clean > q3 + 1.5 * iqr)
    z = np.abs(stats.zscore(clean, nan_policy="omit"))
    z_mask = z > 3
    med = clean.median()
    mad = np.median(np.abs(clean - med)) or 1.0
    mod_z = 0.6745 * (clean - med) / mad
    mod_mask = np.abs(mod_z) > 3.5
    iso_count = 0
    try:
        sample = clean
        if len(sample) > 5000:
            sample = sample.sample(5000, random_state=42)
        preds = IsolationForest(random_state=42, contamination="auto").fit_predict(
            sample.to_numpy().reshape(-1, 1)
        )
        iso_count = int((preds == -1).sum())
    except Exception:  # noqa: BLE001
        iso_count = 0
    return {
        "iqr_count": int(iqr_mask.sum()),
        "zscore_count": int(np.nansum(z_mask)),
        "modified_z_count": int(mod_mask.sum()),
        "isolation_forest_count": iso_count,
    }


def correlation_matrix(df: pd.DataFrame, numeric_cols: list[str]) -> dict[str, Any]:
    if len(numeric_cols) < 2:
        return {
            "columns": numeric_cols,
            "pearson": [],
            "spearman": [],
            "kendall": [],
            "high_pairs": [],
        }
    sub = df[numeric_cols].apply(pd.to_numeric, errors="coerce")
    pearson = sub.corr(method="pearson")
    spearman = sub.corr(method="spearman")
    # Kendall can be expensive — limit columns
    kendall_cols = numeric_cols[:12]
    kendall = (
        sub[kendall_cols].corr(method="kendall") if len(kendall_cols) >= 2 else pearson.iloc[:0, :0]
    )
    high_pairs: list[dict[str, Any]] = []
    for i, a in enumerate(numeric_cols):
        for b in numeric_cols[i + 1 :]:
            val = pearson.loc[a, b]
            if pd.notna(val) and abs(float(val)) >= 0.9:
                high_pairs.append({"a": a, "b": b, "pearson": _safe_float(val)})
    return {
        "columns": numeric_cols,
        "pearson": pearson.replace({np.nan: None}).values.tolist(),
        "spearman": spearman.replace({np.nan: None}).values.tolist(),
        "kendall": {
            "columns": kendall_cols,
            "matrix": kendall.replace({np.nan: None}).values.tolist(),
        },
        "high_pairs": high_pairs,
    }


def detect_target(df: pd.DataFrame, kinds: dict[str, ColumnKind]) -> dict[str, Any]:
    candidates: list[tuple[str, float, str]] = []
    for col, kind in kinds.items():
        lower = col.lower()
        score = 0.0
        reason = []
        if lower in TARGET_NAME_HINTS:
            score += 0.55
            reason.append("name_hint")
        for hint in TARGET_NAME_HINTS:
            if hint in lower and lower not in ID_NAME_HINTS:
                score += 0.25
                reason.append(f"contains:{hint}")
                break
        nunique = int(df[col].nunique(dropna=True))
        if kind in {ColumnKind.BOOLEAN} or (kind == ColumnKind.INTEGER and 2 <= nunique <= 20):
            score += 0.2
            reason.append("low_cardinality")
        if kind in {ColumnKind.FLOAT, ColumnKind.INTEGER} and nunique > 20:
            score += 0.1
            reason.append("numeric_spread")
        if kind in {ColumnKind.ID, ColumnKind.CONSTANT}:
            score -= 0.5
        score = max(0.0, min(1.0, score))
        if score > 0:
            candidates.append((col, score, ",".join(reason) or "heuristic"))
    candidates.sort(key=lambda x: x[1], reverse=True)
    if not candidates:
        return {"column": None, "confidence": 0.0, "reason": "none", "candidates": []}
    best = candidates[0]
    return {
        "column": best[0],
        "confidence": best[1],
        "reason": best[2],
        "candidates": [{"column": c, "confidence": s, "reason": r} for c, s, r in candidates[:5]],
    }


def detect_problem_type(
    df: pd.DataFrame, target: dict[str, Any], kinds: dict[str, ColumnKind]
) -> ProblemType:
    col = target.get("column")
    datetime_cols = [c for c, k in kinds.items() if k is ColumnKind.DATETIME]
    if datetime_cols and col and kinds.get(col) in {ColumnKind.FLOAT, ColumnKind.INTEGER}:
        return ProblemType.TIME_SERIES
    if not col:
        if len(df.columns) >= 3:
            return ProblemType.CLUSTERING_CANDIDATE
        return ProblemType.UNKNOWN
    kind = kinds.get(col, ColumnKind.MIXED)
    nunique = int(df[col].nunique(dropna=True))
    if kind is ColumnKind.BOOLEAN or nunique == 2:
        return ProblemType.BINARY_CLASSIFICATION
    if kind in {ColumnKind.CATEGORICAL, ColumnKind.INTEGER} and 3 <= nunique <= 50:
        return ProblemType.MULTICLASS_CLASSIFICATION
    if kind in {ColumnKind.FLOAT, ColumnKind.INTEGER} and nunique > 50:
        return ProblemType.REGRESSION
    if "fraud" in col.lower() or "anomaly" in col.lower():
        return ProblemType.ANOMALY_DETECTION_CANDIDATE
    if "recommend" in col.lower() or "rating" in col.lower():
        return ProblemType.RECOMMENDATION
    return ProblemType.UNKNOWN


def quality_scores(df: pd.DataFrame, column_reports: list[dict[str, Any]]) -> dict[str, Any]:
    rows, cols = df.shape
    total_cells = max(rows * cols, 1)
    missing_cells = int(df.isna().sum().sum())
    completeness = 100.0 * (1 - missing_cells / total_cells)
    dup_ratio = float(df.duplicated().mean()) if rows else 0.0
    uniqueness = 100.0 * (1 - dup_ratio)
    mixed = sum(1 for c in column_reports if c.get("kind") == ColumnKind.MIXED.value)
    validity = 100.0 * (1 - mixed / max(cols, 1))
    const = sum(1 for c in column_reports if c.get("kind") == ColumnKind.CONSTANT.value)
    consistency = 100.0 * (1 - const / max(cols, 1))
    overall = 0.4 * completeness + 0.2 * uniqueness + 0.2 * validity + 0.2 * consistency
    if overall >= 90:
        health = DatasetHealth.EXCELLENT
    elif overall >= 75:
        health = DatasetHealth.GOOD
    elif overall >= 60:
        health = DatasetHealth.FAIR
    elif overall >= 40:
        health = DatasetHealth.POOR
    else:
        health = DatasetHealth.CRITICAL
    return {
        "completeness": round(completeness, 2),
        "consistency": round(consistency, 2),
        "validity": round(validity, 2),
        "uniqueness": round(uniqueness, 2),
        "overall": round(overall, 2),
        "health": health.value,
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_cells": missing_cells,
        "missing_pct": round(100.0 * missing_cells / total_cells, 4),
    }


def leakage_report(
    df: pd.DataFrame, kinds: dict[str, ColumnKind], target: dict[str, Any], corr: dict[str, Any]
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for col, kind in kinds.items():
        if kind is ColumnKind.ID:
            findings.append(
                {
                    "type": "identifier",
                    "column": col,
                    "severity": "high",
                    "detail": "Likely identifier",
                }
            )
    target_col = target.get("column")
    if target_col and target_col in df.columns:
        y = df[target_col]
        for col, kind in kinds.items():
            if col == target_col:
                continue
            if kind in {ColumnKind.FLOAT, ColumnKind.INTEGER, ColumnKind.BOOLEAN}:
                try:
                    x = pd.to_numeric(df[col], errors="coerce")
                    yt = (
                        pd.to_numeric(y, errors="coerce")
                        if not pd.api.types.is_numeric_dtype(y)
                        else y
                    )
                    mask = x.notna() & yt.notna()
                    if mask.sum() < 20:
                        continue
                    r = float(np.corrcoef(x[mask], yt[mask])[0, 1])
                    if abs(r) >= 0.98:
                        findings.append(
                            {
                                "type": "near_perfect_predictor",
                                "column": col,
                                "severity": "critical",
                                "detail": f"corr(target)={r:.4f}",
                            }
                        )
                    elif abs(r) >= 0.9:
                        findings.append(
                            {
                                "type": "suspicious_feature",
                                "column": col,
                                "severity": "medium",
                                "detail": f"corr(target)={r:.4f}",
                            }
                        )
                except Exception:  # noqa: BLE001
                    pass
            lower = col.lower()
            if any(tok in lower for tok in ("future", "next_", "label_", "target_")):
                findings.append(
                    {
                        "type": "future_column",
                        "column": col,
                        "severity": "high",
                        "detail": "Name suggests post-outcome information",
                    }
                )
            if kinds.get(col) is ColumnKind.DATETIME and any(
                tok in lower for tok in ("end_", "close", "settled", "completed_at")
            ):
                findings.append(
                    {
                        "type": "timestamp_leakage",
                        "column": col,
                        "severity": "medium",
                        "detail": "Datetime may leak outcome timing",
                    }
                )
    for pair in corr.get("high_pairs", []):
        findings.append(
            {
                "type": "perfect_correlation",
                "column": f"{pair['a']}~{pair['b']}",
                "severity": "medium",
                "detail": f"pearson={pair.get('pearson')}",
            }
        )
    if target_col and int(df.duplicated(subset=[target_col]).sum()) == len(df) - 1 and len(df) > 1:
        findings.append(
            {
                "type": "duplicate_targets",
                "column": target_col,
                "severity": "low",
                "detail": "Target nearly constant across rows",
            }
        )
    return {"findings": findings, "count": len(findings)}


def missing_pattern(df: pd.DataFrame, max_rows: int = 200) -> dict[str, Any]:
    sample = df.head(max_rows)
    matrix = sample.isna().astype(int).values.tolist()
    return {
        "columns": list(df.columns.astype(str)),
        "rows_sampled": int(len(sample)),
        "matrix": matrix,
        "per_column": {c: int(df[c].isna().sum()) for c in df.columns},
    }


def profile_dataframe(df: pd.DataFrame, *, file_size_bytes: int | None = None) -> dict[str, Any]:
    """Run full deterministic profile. Does not mutate training data."""
    working = df.copy()
    rows, cols = working.shape
    kinds = {str(c): infer_column_kind(working[c], str(c)) for c in working.columns}
    # coerce datetime-ish
    for c, kind in list(kinds.items()):
        if kind is ColumnKind.DATETIME and not pd.api.types.is_datetime64_any_dtype(working[c]):
            working[c] = pd.to_datetime(working[c], errors="coerce", utc=True)

    column_reports: list[dict[str, Any]] = []
    for col in working.columns:
        name = str(col)
        series = working[col]
        kind = kinds[name]
        missing = int(series.isna().sum())
        nunique = int(series.nunique(dropna=True))
        report: dict[str, Any] = {
            "name": name,
            "kind": kind.value,
            "dtype": str(series.dtype),
            "missing": missing,
            "missing_pct": round(100.0 * missing / max(rows, 1), 4),
            "unique": nunique,
            "cardinality": nunique,
            "nearly_constant": bool(nunique <= 2 and rows > 10),
        }
        if kind in {ColumnKind.INTEGER, ColumnKind.FLOAT}:
            report["statistics"] = profile_numeric(series)
            report["outliers"] = outlier_report(series)
        elif kind in {ColumnKind.CATEGORICAL, ColumnKind.BOOLEAN}:
            report["categorical"] = profile_categorical(series)
        elif kind is ColumnKind.TEXT:
            report["text"] = profile_text(series)
        elif kind is ColumnKind.DATETIME:
            report["datetime"] = profile_datetime(series)
        column_reports.append(report)

    numeric_cols = [
        c
        for c, k in kinds.items()
        if k in {ColumnKind.INTEGER, ColumnKind.FLOAT} and working[c].nunique() > 1
    ]
    corr = correlation_matrix(working, numeric_cols[:40])
    target = detect_target(working, kinds)
    problem = detect_problem_type(working, target, kinds)
    quality = quality_scores(working, column_reports)
    leakage = leakage_report(working, kinds, target, corr)
    missing_info = missing_pattern(working)

    mem = int(working.memory_usage(deep=True).sum())
    return {
        "overview": {
            "rows": rows,
            "columns": cols,
            "memory_bytes": mem,
            "file_size_bytes": file_size_bytes,
            "duplicate_rows": int(working.duplicated().sum()),
            "column_order": [str(c) for c in working.columns],
        },
        "columns": column_reports,
        "correlations": corr,
        "missing": missing_info,
        "target": target,
        "problem_type": problem.value,
        "quality": quality,
        "leakage": leakage,
        "recommendations": _recommendations(quality, leakage, target, problem, column_reports),
    }


def _recommendations(
    quality: dict[str, Any],
    leakage: dict[str, Any],
    target: dict[str, Any],
    problem: ProblemType,
    columns: list[dict[str, Any]],
) -> list[str]:
    tips: list[str] = []
    if quality["missing_pct"] > 1:
        tips.append(
            f"Address missing values ({quality['missing_pct']}% of cells) before modeling — Phase 5 cleaning."
        )
    if quality["duplicate_rows"]:
        tips.append(f"Remove or investigate {quality['duplicate_rows']} duplicate rows.")
    for finding in leakage.get("findings", [])[:8]:
        tips.append(
            f"Leakage/{finding['type']}: review column `{finding['column']}` ({finding['detail']})."
        )
    for col in columns:
        if col.get("kind") == ColumnKind.ID.value:
            tips.append(f"Consider dropping identifier `{col['name']}` from features.")
        outs = col.get("outliers") or {}
        if outs.get("iqr_count", 0) > 0 and col.get("kind") in {
            ColumnKind.FLOAT.value,
            ColumnKind.INTEGER.value,
        }:
            tips.append(
                f"`{col['name']}` has {outs['iqr_count']} IQR outliers (do not auto-clean here)."
            )
    if target.get("column"):
        tips.append(
            f"Inferred target `{target['column']}` (confidence {target['confidence']:.0%}) for {problem.value}."
        )
    else:
        tips.append("No clear target detected — confirm label column manually.")
    tips.append("Recommended next step: Proceed to Data Cleaning (Phase 5).")
    return tips

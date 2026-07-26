"""Deterministic cleaning plan generation and recipe execution."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest
from sklearn.experimental import enable_iterative_imputer  # noqa: F401
from sklearn.impute import IterativeImputer, KNNImputer
from sklearn.neighbors import LocalOutlierFactor

from atlas_preparation.domain import (
    ENGLISH_STOPWORDS,
    ID_NAME_HINTS,
    OutlierMethod,
    StepKind,
)

_MISSING_STRATEGY_MAP: dict[str, StepKind] = {
    "mean": StepKind.IMPUTE_MEAN,
    "median": StepKind.IMPUTE_MEDIAN,
    "mode": StepKind.IMPUTE_MODE,
    "constant": StepKind.IMPUTE_CONSTANT,
    "ffill": StepKind.IMPUTE_FFILL,
    "bfill": StepKind.IMPUTE_BFILL,
    "interpolate": StepKind.IMPUTE_INTERPOLATE,
    "knn": StepKind.IMPUTE_KNN,
    "iterative": StepKind.IMPUTE_ITERATIVE,
    "drop_rows": StepKind.DROP_ROWS_MISSING,
    "drop_columns": StepKind.DROP_COLUMN,
}


def _is_id_name(name: str) -> bool:
    n = name.strip().lower()
    return n in ID_NAME_HINTS or n.endswith("_id") or n.endswith("id")


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def quality_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    rows, cols = df.shape
    missing = int(df.isna().sum().sum())
    cells = max(rows * cols, 1)
    duplicates = int(df.duplicated().sum())
    missing_pct = round(100.0 * missing / cells, 4)
    dup_pct = round(100.0 * duplicates / max(rows, 1), 4)
    score = max(0.0, 100.0 - missing_pct * 0.6 - dup_pct * 0.4)
    if score >= 90:
        health = "excellent"
    elif score >= 75:
        health = "good"
    elif score >= 55:
        health = "fair"
    elif score >= 35:
        health = "poor"
    else:
        health = "critical"
    return {
        "rows": int(rows),
        "columns": int(cols),
        "missing_cells": missing,
        "missing_pct": missing_pct,
        "duplicate_rows": duplicates,
        "duplicate_pct": dup_pct,
        "quality_overall": round(score, 2),
        "health": health,
    }


def _outlier_mask(series: pd.Series, method: OutlierMethod) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    valid = numeric.dropna()
    mask = pd.Series(False, index=series.index)
    if len(valid) < 8:
        return mask
    if method is OutlierMethod.IQR:
        q1, q3 = valid.quantile(0.25), valid.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return mask
        low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
        mask = (numeric < low) | (numeric > high)
    elif method is OutlierMethod.ZSCORE:
        mu, sigma = valid.mean(), valid.std(ddof=0)
        if sigma == 0 or np.isnan(sigma):
            return mask
        z = (numeric - mu).abs() / sigma
        mask = z > 3
    elif method is OutlierMethod.MODIFIED_Z:
        med = valid.median()
        mad = (valid - med).abs().median()
        if mad == 0 or np.isnan(mad):
            return mask
        mz = 0.6745 * (numeric - med).abs() / mad
        mask = mz > 3.5
    elif method is OutlierMethod.ISOLATION_FOREST:
        model = IsolationForest(contamination=0.05, random_state=42)
        preds = model.fit_predict(valid.to_frame())
        bad = set(valid.index[preds == -1])
        mask = series.index.to_series().isin(bad)
    elif method is OutlierMethod.LOF:
        n = min(20, max(5, len(valid) // 5))
        if len(valid) <= n:
            return mask
        model = LocalOutlierFactor(n_neighbors=n, contamination=0.05)
        preds = model.fit_predict(valid.to_frame())
        bad = set(valid.index[preds == -1])
        mask = series.index.to_series().isin(bad)
    elif method is OutlierMethod.DBSCAN:
        values = valid.to_numpy().reshape(-1, 1)
        # Scale-free eps relative to IQR
        q1, q3 = float(valid.quantile(0.25)), float(valid.quantile(0.75))
        scale = max(q3 - q1, float(valid.std(ddof=0) or 1.0), 1e-6)
        clustering = DBSCAN(eps=0.5 * scale, min_samples=max(3, len(valid) // 20)).fit(values)
        labels = clustering.labels_
        bad = set(valid.index[labels == -1])
        mask = series.index.to_series().isin(bad)
    return mask.fillna(False)


def _infer_kind(series: pd.Series, meta: dict[str, Any]) -> str:
    kind = meta.get("kind")
    if kind:
        return str(kind)
    if pd.api.types.is_numeric_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if series.nunique(dropna=True) <= max(20, int(0.05 * len(series))):
        return "categorical"
    avg_len = series.dropna().astype(str).str.len().mean() if len(series.dropna()) else 0
    return "text" if avg_len and avg_len > 40 else "categorical"


def _resolve_missing_step(kind: str, missing_strategy: str, missing_pct: float) -> StepKind:
    if missing_strategy == "auto":
        if missing_pct >= 80:
            return StepKind.DROP_COLUMN
        if missing_pct >= 60:
            return StepKind.DROP_ROWS_MISSING
        if kind in {"integer", "float"}:
            return StepKind.IMPUTE_MEDIAN
        if kind in {"categorical", "boolean"}:
            return StepKind.IMPUTE_MODE
        if kind == "datetime":
            return StepKind.IMPUTE_FFILL
        return StepKind.IMPUTE_CONSTANT

    mapped = _MISSING_STRATEGY_MAP.get(missing_strategy)
    if mapped is None:
        return StepKind.IMPUTE_MEDIAN if kind in {"integer", "float"} else StepKind.IMPUTE_MODE
    if mapped in {
        StepKind.IMPUTE_KNN,
        StepKind.IMPUTE_ITERATIVE,
        StepKind.IMPUTE_MEAN,
        StepKind.IMPUTE_MEDIAN,
        StepKind.IMPUTE_INTERPOLATE,
    } and kind not in {
        "integer",
        "float",
    }:
        return StepKind.IMPUTE_MODE
    return mapped


def _similar_categories(values: list[str], threshold: float = 0.86) -> dict[str, str]:
    """Map rare/near-duplicate category labels onto a canonical form."""
    mapping: dict[str, str] = {}
    canon: list[str] = []
    for value in sorted(values, key=len, reverse=True):
        matched = None
        for c in canon:
            if SequenceMatcher(None, value, c).ratio() >= threshold:
                matched = c
                break
        if matched is None:
            canon.append(value)
            mapping[value] = value
        else:
            mapping[value] = matched
    return {k: v for k, v in mapping.items() if k != v}


def _near_duplicate_mask(df: pd.DataFrame) -> pd.Series:
    """Flag rows that collide after aggressive string normalization (near-exact)."""
    if df.empty:
        return pd.Series(False, index=df.index)
    normalized = df.copy()
    for col in normalized.columns:
        if pd.api.types.is_numeric_dtype(normalized[col]) or pd.api.types.is_datetime64_any_dtype(
            normalized[col]
        ):
            continue
        normalized[col] = (
            normalized[col]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.replace(r"\s+", " ", regex=True)
            .replace({"nan": "", "none": ""})
        )
    # Mark all but first in each near-duplicate group
    return normalized.duplicated(keep="first")


def build_cleaning_plan(
    df: pd.DataFrame,
    profile: dict[str, Any] | None = None,
    *,
    strategies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a reproducible cleaning recipe from dataframe (+ optional profile)."""
    strategies = strategies or {}
    missing_strategy = str(strategies.get("missing", "auto"))
    outlier_action = strategies.get("outlier_action", "cap")  # remove|cap|winsorize|leave
    outlier_method = OutlierMethod(strategies.get("outlier_method", OutlierMethod.IQR.value))
    drop_ids = bool(strategies.get("drop_id_columns", True))
    drop_duplicates = bool(strategies.get("drop_duplicates", True))
    drop_near_duplicates = bool(strategies.get("drop_near_duplicates", True))
    drop_constant = bool(strategies.get("drop_constant", True))
    drop_empty = bool(strategies.get("drop_empty", True))
    merge_categories = bool(strategies.get("merge_categories", True))
    remove_stopwords = bool(strategies.get("remove_stopwords", False))
    clip_impossible = bool(strategies.get("clip_impossible", True))
    reorder = strategies.get("column_order")

    profile_cols = {c["name"]: c for c in (profile or {}).get("columns", []) if isinstance(c, dict)}
    steps: list[dict[str, Any]] = []
    order = 1

    def add_step(
        kind: StepKind,
        column: str | None,
        params: dict[str, Any],
        reason: str,
        expected_impact: str,
    ) -> None:
        nonlocal order
        steps.append(
            {
                "order": order,
                "kind": kind.value,
                "column": column,
                "params": params,
                "reason": reason,
                "expected_impact": expected_impact,
            }
        )
        order += 1

    # Empty / constant columns
    for col in list(df.columns):
        name = str(col)
        series = df[col]
        if drop_empty and (series.isna().all() or (series.astype(str).str.strip() == "").all()):
            add_step(StepKind.DROP_EMPTY, name, {}, "Column is empty", "Removes unusable feature")
            continue
        nunique = int(series.nunique(dropna=True))
        if drop_constant and nunique <= 1 and len(series) > 1:
            add_step(
                StepKind.DROP_CONSTANT,
                name,
                {},
                "Column is constant",
                "Removes zero-variance feature",
            )

    # ID columns (leakage risk)
    if drop_ids:
        for col in df.columns:
            name = str(col)
            kind = (profile_cols.get(name) or {}).get("kind")
            if kind == "id" or _is_id_name(name):
                if any(s["column"] == name and str(s["kind"]).startswith("drop_") for s in steps):
                    continue
                # Duplicate IDs recommendation when non-unique
                if int(df[col].duplicated().sum()) > 0:
                    add_step(
                        StepKind.DROP_DUPLICATE_IDS,
                        name,
                        {"keep": "first"},
                        f"Duplicate IDs detected in `{name}`",
                        "Keep first occurrence of each ID",
                    )
                add_step(
                    StepKind.DROP_COLUMN,
                    name,
                    {"cause": "identifier"},
                    "Likely identifier / leakage risk",
                    "Reduces leakage risk",
                )

    dropped = {s["column"] for s in steps if str(s["kind"]).startswith("drop_") and s.get("column")}

    # Missing value strategies
    for col in df.columns:
        name = str(col)
        if name in dropped:
            continue
        series = df[col]
        missing_pct = float(series.isna().mean() * 100)
        if missing_pct <= 0:
            continue
        kind = _infer_kind(series, profile_cols.get(name) or {})
        step_kind = _resolve_missing_step(kind, missing_strategy, missing_pct)
        params: dict[str, Any] = {"missing_pct": missing_pct}
        if step_kind is StepKind.IMPUTE_CONSTANT:
            params["fill_value"] = "" if kind == "text" else "unknown"
        if step_kind is StepKind.DROP_COLUMN:
            reason = f"{missing_pct:.1f}% missing — drop column"
            expected = f"Drop sparsely populated `{name}`"
            dropped.add(name)
        elif step_kind is StepKind.DROP_ROWS_MISSING:
            reason = f"{missing_pct:.1f}% missing — drop affected rows"
            expected = f"Drop rows missing `{name}`"
        else:
            reason = f"{kind} missing ({missing_pct:.1f}%) → {step_kind.value}"
            expected = f"Reduce missingness in `{name}`"
        add_step(step_kind, name, params, reason, expected)

    # Exact duplicates
    if drop_duplicates and int(df.duplicated().sum()) > 0:
        add_step(
            StepKind.DROP_DUPLICATES,
            None,
            {"subset": None},
            f"{int(df.duplicated().sum())} exact duplicate rows detected",
            "Remove exact duplicates",
        )

    # Near duplicates
    if drop_near_duplicates:
        near = _near_duplicate_mask(df)
        if int(near.sum()) > 0:
            add_step(
                StepKind.DROP_NEAR_DUPLICATES,
                None,
                {"count": int(near.sum())},
                f"{int(near.sum())} near-duplicate rows after normalization",
                "Remove near-duplicate records",
            )

    # Outliers
    if outlier_action != "leave":
        for col in df.columns:
            name = str(col)
            if name in dropped:
                continue
            series = df[col]
            if not pd.api.types.is_numeric_dtype(series):
                continue
            mask = _outlier_mask(series, outlier_method)
            count = int(mask.sum())
            if count == 0:
                continue
            if outlier_action == "remove":
                kind = StepKind.OUTLIER_REMOVE
            elif outlier_action == "winsorize":
                kind = StepKind.OUTLIER_WINSORIZE
            else:
                kind = StepKind.OUTLIER_CAP
            add_step(
                kind,
                name,
                {"method": outlier_method.value, "count": count},
                f"{count} outliers via {outlier_method.value}",
                f"{outlier_action} outliers in `{name}`",
            )

    # Categorical normalize + merge similar + unknown
    for col in df.columns:
        name = str(col)
        if name in dropped:
            continue
        series = df[col]
        if pd.api.types.is_numeric_dtype(series) or pd.api.types.is_datetime64_any_dtype(series):
            continue
        if (
            series.dtype != object
            and str(series.dtype) != "string"
            and not isinstance(series.dtype, pd.CategoricalDtype)
        ):
            continue
        sample = series.dropna().astype(str).head(500)
        if sample.empty:
            continue
        if (sample != sample.str.strip()).any() or (sample != sample.str.lower()).any():
            add_step(
                StepKind.CATEGORICAL_NORMALIZE,
                name,
                {"case": "lower", "trim": True},
                "Inconsistent casing/whitespace",
                "Normalize categories",
            )
        cats = sorted({str(v).strip().lower() for v in sample.unique()})
        if merge_categories and 2 < len(cats) <= 40:
            merges = _similar_categories(cats)
            if merges:
                add_step(
                    StepKind.CATEGORICAL_MERGE,
                    name,
                    {"mapping": merges},
                    f"Merge {len(merges)} similar category label(s)",
                    "Collapse near-duplicate categories",
                )
        # Unknown / placeholder tokens
        unknown_tokens = {"?", "unknown", "n/a", "na", "null", "none", "-"}
        if any(str(v).strip().lower() in unknown_tokens for v in sample):
            add_step(
                StepKind.CATEGORICAL_UNKNOWN,
                name,
                {"tokens": sorted(unknown_tokens), "replacement": "unknown"},
                "Placeholder unknown values detected",
                "Standardize unknown tokens",
            )

    # Numeric inf / impossible / clip
    for col in df.columns:
        name = str(col)
        if name in dropped:
            continue
        series = df[col]
        if not pd.api.types.is_numeric_dtype(series):
            continue
        numeric = pd.to_numeric(series, errors="coerce")
        if bool(np.isinf(numeric).any()):
            add_step(
                StepKind.NUMERIC_CLEAN_INF,
                name,
                {},
                "Infinite values detected",
                "Replace ±inf with NaN",
            )
        if clip_impossible:
            # Heuristic impossible ranges for common domains
            lower_name = name.lower()
            bounds: dict[str, float] = {}
            if any(k in lower_name for k in ("age", "pct", "percent", "ratio", "prob")):
                if "age" in lower_name:
                    bounds = {"min": 0, "max": 120}
                elif any(k in lower_name for k in ("pct", "percent", "prob", "ratio")):
                    bounds = {"min": 0, "max": 100 if "ratio" not in lower_name else 1}
            if bounds:
                outside = ((numeric < bounds["min"]) | (numeric > bounds["max"])).sum()
                if int(outside) > 0:
                    add_step(
                        StepKind.NUMERIC_IMPOSSIBLE,
                        name,
                        bounds,
                        f"{int(outside)} values outside plausible range {bounds}",
                        "Clip impossible numeric values",
                    )

    # Datetime parse
    for col in df.columns:
        name = str(col)
        if name in dropped:
            continue
        meta = profile_cols.get(name) or {}
        if meta.get("kind") == "datetime" or "date" in name.lower() or "time" in name.lower():
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                add_step(
                    StepKind.DATETIME_PARSE,
                    name,
                    {"utc": True},
                    "Datetime-like column needs standardized parsing",
                    "Normalize timestamps to UTC",
                )

    # Text normalize
    for col in df.columns:
        name = str(col)
        if name in dropped:
            continue
        meta = profile_cols.get(name) or {}
        kind = _infer_kind(df[col], meta)
        if kind != "text":
            continue
        add_step(
            StepKind.TEXT_NORMALIZE,
            name,
            {
                "lowercase": True,
                "strip": True,
                "unicode": "NFKC",
                "remove_stopwords": remove_stopwords,
            },
            "Text column hygiene",
            "Normalize unicode/whitespace/control characters",
        )

    # Optional explicit reorder
    if isinstance(reorder, list) and reorder:
        add_step(
            StepKind.REORDER_COLUMNS,
            None,
            {"columns": [str(c) for c in reorder]},
            "Explicit column order requested",
            "Reorder columns for ML-ready layout",
        )

    before = quality_snapshot(df)
    preview = apply_recipe(df, steps)
    after = quality_snapshot(preview)
    improvement = {
        "missing_pct_delta": round(before["missing_pct"] - after["missing_pct"], 4),
        "duplicate_pct_delta": round(before["duplicate_pct"] - after["duplicate_pct"], 4),
        "quality_delta": round(after["quality_overall"] - before["quality_overall"], 4),
        "rows_delta": after["rows"] - before["rows"],
        "columns_delta": after["columns"] - before["columns"],
    }
    summary = (
        f"Proposed {len(steps)} cleaning step(s). "
        f"Quality {before['quality_overall']} → {after['quality_overall']} "
        f"(Δ {improvement['quality_delta']})."
    )
    return {
        "steps": steps,
        "before": before,
        "after": after,
        "improvement": improvement,
        "summary": summary,
        "graph": {
            "nodes": [
                {"id": f"s{s['order']}", "label": s["kind"], "column": s.get("column")}
                for s in steps
            ],
            "edges": [
                {"from": f"s{steps[i]['order']}", "to": f"s{steps[i + 1]['order']}"}
                for i in range(len(steps) - 1)
            ],
        },
        "recommendations": [
            {
                "column": s.get("column"),
                "kind": s["kind"],
                "reason": s["reason"],
                "expected_impact": s["expected_impact"],
            }
            for s in steps
        ],
    }


def apply_recipe(df: pd.DataFrame, steps: list[dict[str, Any]]) -> pd.DataFrame:
    """Execute a cleaning recipe. Never mutates the input frame."""
    working = df.copy()
    for step in sorted(steps, key=lambda s: int(s.get("order", 0))):
        kind = StepKind(step["kind"])
        col = step.get("column")
        params = step.get("params") or {}

        if kind in {StepKind.DROP_COLUMN, StepKind.DROP_CONSTANT, StepKind.DROP_EMPTY}:
            if col and col in working.columns:
                working = working.drop(columns=[col])
            continue

        if kind is StepKind.DROP_DUPLICATES:
            working = working.drop_duplicates()
            continue

        if kind is StepKind.DROP_NEAR_DUPLICATES:
            mask = _near_duplicate_mask(working)
            working = working.loc[~mask]
            continue

        if kind is StepKind.DROP_DUPLICATE_IDS and col and col in working.columns:
            working = working.drop_duplicates(subset=[col], keep=params.get("keep", "first"))
            continue

        if kind is StepKind.REORDER_COLUMNS:
            cols = [c for c in params.get("columns", []) if c in working.columns]
            rest = [c for c in working.columns if c not in cols]
            working = working[cols + rest]
            continue

        if kind is StepKind.DROP_ROWS_MISSING and col and col in working.columns:
            working = working.dropna(subset=[col])
            continue

        if col is None or col not in working.columns:
            continue

        series = working[col]

        if kind is StepKind.IMPUTE_MEAN:
            working[col] = pd.to_numeric(series, errors="coerce").fillna(
                pd.to_numeric(series, errors="coerce").mean()
            )
        elif kind is StepKind.IMPUTE_MEDIAN:
            working[col] = pd.to_numeric(series, errors="coerce").fillna(
                pd.to_numeric(series, errors="coerce").median()
            )
        elif kind is StepKind.IMPUTE_MODE:
            mode = series.mode(dropna=True)
            fill = mode.iloc[0] if not mode.empty else ""
            working[col] = series.fillna(fill)
        elif kind is StepKind.IMPUTE_CONSTANT:
            working[col] = series.fillna(params.get("fill_value", ""))
        elif kind is StepKind.IMPUTE_FFILL:
            working[col] = series.ffill()
        elif kind is StepKind.IMPUTE_BFILL:
            working[col] = series.bfill()
        elif kind is StepKind.IMPUTE_INTERPOLATE:
            working[col] = pd.to_numeric(series, errors="coerce").interpolate(
                limit_direction="both"
            )
        elif kind is StepKind.IMPUTE_KNN:
            numeric = pd.to_numeric(series, errors="coerce")
            frame = numeric.to_frame()
            if frame.isna().all().all():
                continue
            imputed = KNNImputer(n_neighbors=min(5, max(1, len(frame) - 1))).fit_transform(frame)
            working[col] = imputed[:, 0]
        elif kind is StepKind.IMPUTE_ITERATIVE:
            numeric = pd.to_numeric(series, errors="coerce")
            frame = numeric.to_frame()
            if frame.isna().all().all():
                continue
            imputed = IterativeImputer(random_state=42, max_iter=10).fit_transform(frame)
            working[col] = imputed[:, 0]
        elif kind is StepKind.OUTLIER_REMOVE:
            method = OutlierMethod(params.get("method", OutlierMethod.IQR.value))
            mask = _outlier_mask(series, method)
            working = working.loc[~mask]
        elif kind in {StepKind.OUTLIER_CAP, StepKind.OUTLIER_WINSORIZE}:
            numeric = pd.to_numeric(series, errors="coerce")
            q_low, q_high = (0.05, 0.95) if kind is StepKind.OUTLIER_WINSORIZE else (0.01, 0.99)
            low, high = numeric.quantile(q_low), numeric.quantile(q_high)
            working[col] = numeric.clip(lower=low, upper=high)
        elif kind is StepKind.CATEGORICAL_NORMALIZE:
            text = series.astype(str)
            if params.get("trim", True):
                text = text.str.strip()
            if params.get("case") == "lower":
                text = text.str.lower()
            working[col] = text.replace({"nan": np.nan, "None": np.nan})
        elif kind is StepKind.CATEGORICAL_MERGE:
            mapping = dict(params.get("mapping") or {})
            text = series.astype(str).str.strip().str.lower()
            working[col] = text.replace(mapping).replace({"nan": np.nan})
        elif kind is StepKind.CATEGORICAL_UNKNOWN:
            tokens = {str(t).lower() for t in params.get("tokens", [])}
            replacement = str(params.get("replacement", "unknown"))
            text = series.astype(str).str.strip().str.lower()
            working[col] = text.where(~text.isin(list(tokens)), other=replacement)
        elif kind is StepKind.NUMERIC_CLEAN_INF:
            numeric = pd.to_numeric(series, errors="coerce")
            working[col] = numeric.replace([np.inf, -np.inf], np.nan)
        elif kind in {StepKind.NUMERIC_CLIP, StepKind.NUMERIC_IMPOSSIBLE}:
            numeric = pd.to_numeric(series, errors="coerce")
            working[col] = numeric.clip(params.get("min"), params.get("max"))
        elif kind is StepKind.DATETIME_PARSE:
            working[col] = pd.to_datetime(
                series, errors="coerce", utc=bool(params.get("utc", True))
            )
        elif kind is StepKind.TEXT_NORMALIZE:
            text = series.astype(str)
            form = str(params.get("unicode", "NFKC"))
            text = text.map(
                lambda s, _form=form: unicodedata.normalize(_form, s) if isinstance(s, str) else s
            )
            if params.get("strip", True):
                text = text.str.strip()
            if params.get("lowercase", True):
                text = text.str.lower()
            text = text.str.replace(r"[\x00-\x1f\x7f]", "", regex=True)
            if params.get("remove_stopwords"):

                def _strip_stops(value: str) -> str:
                    parts = [w for w in re.split(r"\s+", value) if w and w not in ENGLISH_STOPWORDS]
                    return " ".join(parts)

                text = text.map(_strip_stops)
            working[col] = text.replace({"nan": np.nan})
        elif kind is StepKind.CAST_DTYPE:
            target = params.get("dtype", "string")
            if target == "integer":
                working[col] = pd.to_numeric(series, errors="coerce").astype("Int64")
            elif target == "float":
                working[col] = pd.to_numeric(series, errors="coerce")
            elif target == "boolean":
                working[col] = series.map({"true": True, "false": False, "1": True, "0": False})
            elif target == "datetime":
                working[col] = pd.to_datetime(series, errors="coerce", utc=True)
            else:
                working[col] = series.astype(str)
        elif kind is StepKind.RENAME_COLUMN:
            new_name = params.get("new_name")
            if new_name and col in working.columns:
                working = working.rename(columns={col: new_name})

    return working.reset_index(drop=True)


def run_data_cleaning(
    df: pd.DataFrame,
    profile: dict[str, Any] | None = None,
    *,
    strategies: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Agent-facing entry: plan + dry-run quality comparison."""
    plan = build_cleaning_plan(df, profile, strategies=strategies)
    return {
        "recipe": {"version": 1, "steps": plan["steps"]},
        "plan": plan,
        "before": plan["before"],
        "after": plan["after"],
        "improvement": plan["improvement"],
        "summary": plan["summary"],
        "graph": plan["graph"],
        "recommendations": plan.get("recommendations", []),
    }

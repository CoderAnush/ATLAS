"""ATLAS Phase 6 Feature Engineering Engine.

Comprehensive feature engineering with quality validation, pipeline building,
and transformation orchestration. Produces numeric-heavy feature matrices with
quality reports and visualizations.
"""

from __future__ import annotations

import re
import warnings
from typing import Any

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.feature_extraction.text import (
    TfidfVectorizer,
)
from sklearn.feature_selection import VarianceThreshold
from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler,
)

from atlas_feature_store.domain import (
    HOLIDAY_MONTH_DAYS,
    LEAKY_NAME_HINTS,
    TransformKind,
)

warnings.filterwarnings("ignore", category=FutureWarning)


def feature_quality_scores(series: pd.Series) -> dict[str, float]:
    """Calculate feature quality metrics.

    Args:
        series: Feature series to evaluate

    Returns:
        Dictionary with quality metrics:
        - uniqueness: Ratio of unique values to total (0-1)
        - variance: Normalized variance (0-1)
        - missing_pct: Percentage of missing values (0-100)
        - correlation: Placeholder for correlation with target (0)
        - redundancy: Placeholder for redundancy score (0)
        - overall_score: Composite quality score (0-100)
    """
    n = len(series)
    if n == 0:
        return {
            "uniqueness": 0.0,
            "variance": 0.0,
            "missing_pct": 100.0,
            "correlation": 0.0,
            "redundancy": 0.0,
            "overall_score": 0.0,
        }

    # Uniqueness
    uniqueness = series.nunique() / n if n > 0 else 0.0

    # Missing percentage
    missing_pct = (series.isna().sum() / n) * 100

    # Variance (for numeric features)
    variance = 0.0
    if pd.api.types.is_numeric_dtype(series):
        non_null = series.dropna()
        if len(non_null) > 1:
            std = float(non_null.std() or 0.0)
            mean = float(non_null.mean() or 0.0)
            if std > 0:
                variance = min(1.0, abs(std / (mean + 1e-10)))

    # Placeholder scores (require target or full dataset)
    correlation = 0.0
    redundancy = 0.0

    # Overall score (weighted combination)
    overall_score = (
        uniqueness * 30 + variance * 30 + (100 - missing_pct) * 0.3 + 10  # Base score
    )

    return {
        "uniqueness": round(uniqueness, 4),
        "variance": round(variance, 4),
        "missing_pct": round(missing_pct, 2),
        "correlation": correlation,
        "redundancy": redundancy,
        "overall_score": round(overall_score, 2),
    }


def validate_features(
    df: pd.DataFrame,
    corr_threshold: float = 0.95,
) -> dict[str, Any]:
    """Validate features and detect quality issues.

    Args:
        df: DataFrame to validate
        corr_threshold: Correlation threshold for detecting redundant features

    Returns:
        Dictionary with:
        - issues: List of detected issue descriptions
        - drop_candidates: Dictionary mapping reason to list of column names
    """
    issues = []
    drop_candidates: dict[str, list[str]] = {
        "constant": [],
        "near_constant": [],
        "duplicate": [],
        "sparse": [],
        "leaky": [],
        "high_correlation": [],
    }

    # Check for constant features
    for col in df.columns:
        nunique = df[col].nunique()
        if nunique <= 1:
            drop_candidates["constant"].append(col)
            issues.append(f"Constant feature: {col}")

    # Check for near-constant features (>95% single value)
    for col in df.columns:
        if col in drop_candidates["constant"]:
            continue
        value_counts = df[col].value_counts(normalize=True)
        if len(value_counts) > 0 and value_counts.iloc[0] > 0.95:
            drop_candidates["near_constant"].append(col)
            issues.append(f"Near-constant feature (>95%): {col}")

    # Check for duplicate features
    seen_hashes: dict[Any, str] = {}
    for col in df.columns:
        if col in drop_candidates["constant"] or col in drop_candidates["near_constant"]:
            continue
        # Hash the column values
        try:
            col_hash = pd.util.hash_pandas_object(df[col], index=False).sum()
            if col_hash in seen_hashes:
                drop_candidates["duplicate"].append(col)
                issues.append(f"Duplicate feature: {col} (same as {seen_hashes[col_hash]})")
            else:
                seen_hashes[col_hash] = col
        except TypeError:
            pass

    # Check for sparse features (>90% missing)
    for col in df.columns:
        missing_pct = (df[col].isna().sum() / len(df)) * 100
        if missing_pct > 90:
            drop_candidates["sparse"].append(col)
            issues.append(f"Sparse feature (>{missing_pct:.1f}% missing): {col}")

    # Check for leaky features
    for col in df.columns:
        col_lower = col.lower()
        for hint in LEAKY_NAME_HINTS:
            if hint in col_lower:
                drop_candidates["leaky"].append(col)
                issues.append(f"Potentially leaky feature: {col} (contains '{hint}')")
                break

    # Check for high correlation (numeric only)
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if len(numeric_cols) > 1:
        # Remove already flagged columns
        flagged = set()
        for reason_cols in drop_candidates.values():
            flagged.update(reason_cols)
        numeric_cols = [c for c in numeric_cols if c not in flagged]

        if len(numeric_cols) > 1:
            corr_matrix = df[numeric_cols].corr().abs()
            # Get upper triangle
            upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))

            # Find features with correlation above threshold
            for column in upper.columns:
                if (upper[column] > corr_threshold).any():
                    if column not in drop_candidates["high_correlation"]:
                        drop_candidates["high_correlation"].append(column)
                        issues.append(
                            f"High correlation feature: {column} "
                            f"(>{corr_threshold} with another feature)"
                        )

    return {
        "issues": issues,
        "drop_candidates": drop_candidates,
    }


def _safe_column_name(name: str) -> str:
    """Convert column name to safe identifier."""
    # Replace non-alphanumeric with underscore
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", str(name))
    # Ensure starts with letter or underscore
    if safe and not safe[0].isalpha() and safe[0] != "_":
        safe = f"col_{safe}"
    # Limit length
    return safe[:100]


def _detect_problem_type(df: pd.DataFrame, target: str | None) -> str:
    """Detect problem type from target column."""
    if target is None or target not in df.columns:
        return "unknown"

    target_col = df[target]
    nunique = target_col.nunique()

    if pd.api.types.is_numeric_dtype(target_col):
        if nunique <= 10:
            return "classification"
        return "regression"

    return "classification"


def build_feature_pipeline(
    df: pd.DataFrame,
    profile: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build feature engineering pipeline.

    Args:
        df: Input DataFrame
        profile: Optional data profile dict
        config: Optional configuration overrides

    Returns:
        Pipeline dictionary with version, steps, target, problem_type, config
    """
    if config is None:
        config = {}

    target = config.get("target")
    problem_type = _detect_problem_type(df, target)

    # Identify column types
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # Remove target from features
    if target:
        numeric_cols = [c for c in numeric_cols if c != target]
        categorical_cols = [c for c in categorical_cols if c != target]
        datetime_cols = [c for c in datetime_cols if c != target]

    # Identify text columns (long strings)
    text_cols = []
    for col in categorical_cols:
        if df[col].astype(str).str.len().mean() > 50:
            text_cols.append(col)
    categorical_cols = [c for c in categorical_cols if c not in text_cols]

    steps = []

    drop_kind_map = {
        "constant": TransformKind.DROP_CONSTANT,
        "near_constant": TransformKind.DROP_NEAR_CONSTANT,
        "duplicate": TransformKind.DROP_DUPLICATE,
        "sparse": TransformKind.DROP_SPARSE,
        "leaky": TransformKind.DROP_LEAKY,
        "high_correlation": TransformKind.DROP_HIGH_CORR,
    }

    # 1. Drop problematic features
    validation = validate_features(df)
    all_drops = []
    for reason, cols in validation["drop_candidates"].items():
        if cols:
            all_drops.extend(cols)
            steps.append(
                {
                    "kind": drop_kind_map.get(reason, TransformKind.DROP_CONSTANT),
                    "columns": cols,
                    "params": {"reason": reason},
                }
            )

    # Update column lists
    numeric_cols = [c for c in numeric_cols if c not in all_drops]
    categorical_cols = [c for c in categorical_cols if c not in all_drops]
    datetime_cols = [c for c in datetime_cols if c not in all_drops]
    text_cols = [c for c in text_cols if c not in all_drops]

    # 2. Passthrough for remaining clean features
    passthrough_cols = numeric_cols.copy()
    if passthrough_cols:
        steps.append(
            {
                "kind": TransformKind.PASSTHROUGH,
                "columns": passthrough_cols,
                "params": {},
            }
        )

    # 3. DateTime features
    if datetime_cols:
        steps.append(
            {
                "kind": TransformKind.TIME_PARTS,
                "columns": datetime_cols,
                "params": {
                    "parts": [
                        "year",
                        "month",
                        "day",
                        "dayofweek",
                        "hour",
                        "is_weekend",
                        "is_holiday",
                    ],
                    "holiday_month_days": list(HOLIDAY_MONTH_DAYS),
                },
            }
        )

    # 4. Text features
    if text_cols:
        # Limit text columns for performance
        text_cols_limited = text_cols[:3]

        # Text statistics
        steps.append(
            {
                "kind": TransformKind.TEXT_STATS,
                "columns": text_cols_limited,
                "params": {"stats": ["length", "word_count", "unique_words"]},
            }
        )

        # TF-IDF (first text column only)
        if len(text_cols_limited) > 0:
            steps.append(
                {
                    "kind": TransformKind.TFIDF,
                    "columns": [text_cols_limited[0]],
                    "params": {"max_features": 50, "ngram_range": (1, 2)},
                }
            )

    # 5. Categorical encoding
    if categorical_cols:
        # Limit categorical columns
        categorical_cols_limited = categorical_cols[:10]

        # One-hot for low cardinality
        low_card_cols = []
        high_card_cols = []
        for col in categorical_cols_limited:
            if df[col].nunique() <= 10:
                low_card_cols.append(col)
            else:
                high_card_cols.append(col)

        if low_card_cols:
            steps.append(
                {
                    "kind": TransformKind.ONE_HOT,
                    "columns": low_card_cols,
                    "params": {"max_categories": 10},
                }
            )

        if high_card_cols:
            steps.append(
                {
                    "kind": TransformKind.FREQUENCY,
                    "columns": high_card_cols,
                    "params": {},
                }
            )

    # 6. Numeric transformations
    if len(numeric_cols) >= 2:
        # Interactions (limited)
        interaction_pairs = []
        for i, col1 in enumerate(numeric_cols[:4]):
            for col2 in numeric_cols[i + 1 : 5]:
                interaction_pairs.append((col1, col2))
                if len(interaction_pairs) >= 8:
                    break
            if len(interaction_pairs) >= 8:
                break

        if interaction_pairs:
            steps.append(
                {
                    "kind": TransformKind.INTERACTION,
                    "columns": numeric_cols[:5],
                    "params": {"pairs": interaction_pairs},
                }
            )

        # Ratios
        if len(numeric_cols) >= 2:
            ratio_pairs = [(numeric_cols[0], numeric_cols[1])]
            steps.append(
                {
                    "kind": TransformKind.RATIO,
                    "columns": numeric_cols[:2],
                    "params": {"pairs": ratio_pairs},
                }
            )

    # 7. Mathematical transformations
    positive_cols = [c for c in numeric_cols if df[c].min() > 0]
    if positive_cols:
        steps.append(
            {
                "kind": TransformKind.LOG,
                "columns": positive_cols[:5],
                "params": {},
            }
        )

    non_negative_cols = [c for c in numeric_cols if df[c].min() >= 0]
    if non_negative_cols:
        steps.append(
            {
                "kind": TransformKind.SQRT,
                "columns": non_negative_cols[:5],
                "params": {},
            }
        )

    # 8. Binning
    if numeric_cols:
        steps.append(
            {
                "kind": TransformKind.BINNING,
                "columns": numeric_cols[:3],
                "params": {"n_bins": 5, "strategy": "quantile"},
            }
        )

    # 9. Scaling
    if numeric_cols:
        steps.append(
            {
                "kind": TransformKind.STANDARD_SCALE,
                "columns": numeric_cols,
                "params": {},
            }
        )

    # 10. Variance threshold
    steps.append(
        {
            "kind": TransformKind.VARIANCE_THRESHOLD,
            "columns": "__all__",
            "params": {"threshold": 0.01},
        }
    )

    # 11. Dimensionality reduction (if many features)
    if len(numeric_cols) > 20:
        steps.append(
            {
                "kind": TransformKind.PCA,
                "columns": "__all__",
                "params": {"n_components": min(20, len(numeric_cols) // 2)},
            }
        )

    # 12. Placeholder disabled steps
    disabled_steps = [
        {
            "kind": TransformKind.EMBEDDING,
            "columns": text_cols[:1] if text_cols else [],
            "params": {"disabled": True, "reason": "Requires Phase 7 embedding models"},
        },
        {
            "kind": TransformKind.TARGET_ENCODING,
            "columns": categorical_cols[:3] if categorical_cols else [],
            "params": {
                "disabled": True,
                "reason": "Requires Phase 7 target-aware encoding with cross-validation",
            },
        },
        {
            "kind": TransformKind.MUTUAL_INFO,
            "columns": "__all__",
            "params": {"disabled": True, "reason": "Requires Phase 7 target-based selection"},
        },
        {
            "kind": TransformKind.FEATURE_IMPORTANCE,
            "columns": "__all__",
            "params": {"disabled": True, "reason": "Requires Phase 7 model-based importance"},
        },
    ]

    return {
        "version": "1.0.0",
        "steps": steps,
        "disabled_steps": disabled_steps,
        "target": target,
        "problem_type": problem_type,
        "config": config,
        "column_types": {
            "numeric": numeric_cols,
            "categorical": categorical_cols,
            "datetime": datetime_cols,
            "text": text_cols,
        },
    }


def apply_pipeline(
    df: pd.DataFrame,
    steps: list[dict[str, Any]],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Apply feature engineering pipeline to DataFrame.

    Args:
        df: Input DataFrame
        steps: List of pipeline step dictionaries

    Returns:
        Tuple of (transformed_df, report_dict)
    """
    result_df = df.copy()
    applied_steps: list[dict[str, Any]] = []
    feature_scores = {}
    all_new_features = []

    for step_idx, step in enumerate(steps):
        raw_kind = step.get("kind")
        kind = TransformKind(str(raw_kind)) if raw_kind is not None else TransformKind.PASSTHROUGH
        columns = list(step.get("columns") or step.get("input_columns") or [])
        params = step.get("params", {}) or {}
        if step.get("approved") is False:
            continue

        # Skip disabled steps
        if params.get("disabled") or params.get("enabled") is False:
            continue

        step_name = f"step_{step_idx}_{kind.value}"
        new_features = []

        try:
            # Drop operations
            if kind == TransformKind.DROP_CONSTANT:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} constant features",
                    }
                )
                continue

            elif kind == TransformKind.DROP_NEAR_CONSTANT:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} near-constant features",
                    }
                )
                continue

            elif kind == TransformKind.DROP_DUPLICATE:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} duplicate features",
                    }
                )
                continue

            elif kind == TransformKind.DROP_SPARSE:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} sparse features",
                    }
                )
                continue

            elif kind == TransformKind.DROP_LEAKY:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} potentially leaky features",
                    }
                )
                continue

            elif kind == TransformKind.DROP_HIGH_CORR:
                result_df = result_df.drop(columns=columns, errors="ignore")
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Dropped {len(columns)} high-correlation features",
                    }
                )
                continue

            # Passthrough
            elif kind == TransformKind.PASSTHROUGH:
                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Kept {len(columns)} features as-is",
                    }
                )
                continue

            # Time parts
            elif kind == TransformKind.TIME_PARTS:
                parts = params.get("parts", ["year", "month", "day"])
                holiday_days = params.get("holiday_month_days", [])

                for col in columns:
                    if col not in result_df.columns:
                        continue
                    dt_col = pd.to_datetime(result_df[col], errors="coerce")

                    if "year" in parts:
                        feat = f"{col}_year"
                        result_df[_safe_column_name(feat)] = dt_col.dt.year
                        new_features.append(feat)

                    if "month" in parts:
                        feat = f"{col}_month"
                        result_df[_safe_column_name(feat)] = dt_col.dt.month
                        new_features.append(feat)

                    if "day" in parts:
                        feat = f"{col}_day"
                        result_df[_safe_column_name(feat)] = dt_col.dt.day
                        new_features.append(feat)

                    if "dayofweek" in parts:
                        feat = f"{col}_dayofweek"
                        result_df[_safe_column_name(feat)] = dt_col.dt.dayofweek
                        new_features.append(feat)

                    if "hour" in parts:
                        feat = f"{col}_hour"
                        result_df[_safe_column_name(feat)] = dt_col.dt.hour
                        new_features.append(feat)

                    if "is_weekend" in parts:
                        feat = f"{col}_is_weekend"
                        result_df[_safe_column_name(feat)] = (dt_col.dt.dayofweek >= 5).astype(int)
                        new_features.append(feat)

                    if "is_holiday" in parts and holiday_days:
                        feat = f"{col}_is_holiday"
                        holiday_set = {tuple(x) if isinstance(x, list) else x for x in holiday_days}

                        def _is_holiday(x: Any, _holidays: set[Any] = holiday_set) -> int:
                            return int((x.month, x.day) in _holidays) if pd.notna(x) else 0

                        result_df[_safe_column_name(feat)] = dt_col.apply(_is_holiday)
                        new_features.append(feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Extracted {len(new_features)} time features",
                        "new_features": new_features,
                    }
                )

            # Text statistics
            elif kind == TransformKind.TEXT_STATS:
                stats = params.get("stats", ["length", "word_count"])

                for col in columns:
                    if col not in result_df.columns:
                        continue
                    text_col = result_df[col].astype(str)

                    if "length" in stats:
                        feat = f"{col}_length"
                        result_df[_safe_column_name(feat)] = text_col.str.len()
                        new_features.append(feat)

                    if "word_count" in stats:
                        feat = f"{col}_word_count"
                        result_df[_safe_column_name(feat)] = text_col.str.split().str.len()
                        new_features.append(feat)

                    if "unique_words" in stats:
                        feat = f"{col}_unique_words"
                        result_df[_safe_column_name(feat)] = text_col.apply(
                            lambda x: len(set(str(x).split()))
                        )
                        new_features.append(feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Extracted {len(new_features)} text statistics",
                        "new_features": new_features,
                    }
                )

            # TF-IDF
            elif kind == TransformKind.TFIDF:
                max_features = params.get("max_features", 50)
                ngram_range = tuple(params.get("ngram_range", [1, 1]))

                for col in columns:
                    if col not in result_df.columns:
                        continue

                    text_data = result_df[col].fillna("").astype(str)
                    vectorizer = TfidfVectorizer(
                        max_features=max_features,
                        ngram_range=ngram_range,
                        strip_accents="unicode",
                    )

                    try:
                        tfidf_matrix = vectorizer.fit_transform(text_data)
                        feature_names = vectorizer.get_feature_names_out()

                        for i, fname in enumerate(feature_names):
                            feat = f"{col}_tfidf_{fname}"
                            safe_feat = _safe_column_name(feat)
                            result_df[safe_feat] = tfidf_matrix[:, i].toarray().flatten()
                            new_features.append(safe_feat)
                    except Exception:
                        pass

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Created {len(new_features)} TF-IDF features",
                        "new_features": new_features[:10],  # Limit display
                    }
                )

            # One-hot encoding
            elif kind == TransformKind.ONE_HOT:
                max_categories = params.get("max_categories", 10)

                for col in columns:
                    if col not in result_df.columns:
                        continue

                    encoder = OneHotEncoder(
                        sparse_output=False,
                        handle_unknown="ignore",
                        max_categories=max_categories,
                    )

                    try:
                        encoded = encoder.fit_transform(result_df[[col]])
                        categories = encoder.categories_[0]

                        for i, cat in enumerate(categories):
                            feat = f"{col}_{cat}"
                            safe_feat = _safe_column_name(feat)
                            result_df[safe_feat] = encoded[:, i]
                            new_features.append(safe_feat)
                    except Exception:
                        pass

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"One-hot encoded {len(columns)} features -> {len(new_features)} features",
                        "new_features": new_features[:10],
                    }
                )

            # Frequency encoding
            elif kind == TransformKind.FREQUENCY:
                for col in columns:
                    if col not in result_df.columns:
                        continue

                    freq_map = result_df[col].value_counts(normalize=True).to_dict()
                    feat = f"{col}_freq"
                    safe_feat = _safe_column_name(feat)
                    result_df[safe_feat] = result_df[col].map(freq_map).fillna(0)
                    new_features.append(safe_feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Frequency encoded {len(columns)} features",
                        "new_features": new_features,
                    }
                )

            # Interactions
            elif kind == TransformKind.INTERACTION:
                pairs = params.get("pairs", [])

                for col1, col2 in pairs:
                    if col1 in result_df.columns and col2 in result_df.columns:
                        feat = f"{col1}_x_{col2}"
                        safe_feat = _safe_column_name(feat)
                        result_df[safe_feat] = result_df[col1] * result_df[col2]
                        new_features.append(safe_feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Created {len(new_features)} interaction features",
                        "new_features": new_features,
                    }
                )

            # Ratios
            elif kind == TransformKind.RATIO:
                pairs = params.get("pairs", [])

                for col1, col2 in pairs:
                    if col1 in result_df.columns and col2 in result_df.columns:
                        feat = f"{col1}_div_{col2}"
                        safe_feat = _safe_column_name(feat)
                        result_df[safe_feat] = result_df[col1] / (result_df[col2] + 1e-10)
                        result_df[safe_feat] = result_df[safe_feat].replace([np.inf, -np.inf], 0)
                        new_features.append(safe_feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Created {len(new_features)} ratio features",
                        "new_features": new_features,
                    }
                )

            # Log transform
            elif kind == TransformKind.LOG:
                for col in columns:
                    if col in result_df.columns:
                        feat = f"{col}_log"
                        safe_feat = _safe_column_name(feat)
                        result_df[safe_feat] = np.log1p(result_df[col])
                        new_features.append(safe_feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Log-transformed {len(new_features)} features",
                        "new_features": new_features,
                    }
                )

            # Square root
            elif kind == TransformKind.SQRT:
                for col in columns:
                    if col in result_df.columns:
                        feat = f"{col}_sqrt"
                        safe_feat = _safe_column_name(feat)
                        result_df[safe_feat] = np.sqrt(result_df[col].clip(lower=0))
                        new_features.append(safe_feat)

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Square-root transformed {len(new_features)} features",
                        "new_features": new_features,
                    }
                )

            # Binning
            elif kind == TransformKind.BINNING:
                n_bins = params.get("n_bins", 5)

                for col in columns:
                    if col in result_df.columns:
                        try:
                            feat = f"{col}_bin"
                            safe_feat = _safe_column_name(feat)
                            result_df[safe_feat] = pd.qcut(
                                result_df[col],
                                q=n_bins,
                                labels=False,
                                duplicates="drop",
                            )
                            new_features.append(safe_feat)
                        except Exception:
                            pass

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Binned {len(new_features)} features into {n_bins} bins",
                        "new_features": new_features,
                    }
                )

            # Standard scaling
            elif kind == TransformKind.STANDARD_SCALE:
                scaler = StandardScaler()
                cols_to_scale = [c for c in columns if c in result_df.columns]

                if cols_to_scale:
                    numeric_data = result_df[cols_to_scale].select_dtypes(include=[np.number])
                    if not numeric_data.empty:
                        scaled = scaler.fit_transform(numeric_data)
                        for i, col in enumerate(numeric_data.columns):
                            result_df[col] = scaled[:, i]

                applied_steps.append(
                    {
                        "step": step_name,
                        "kind": kind,
                        "action": f"Standard scaled {len(numeric_data.columns)} features",
                    }
                )

            # Variance threshold
            elif kind == TransformKind.VARIANCE_THRESHOLD:
                threshold = params.get("threshold", 0.01)

                numeric_data = result_df.select_dtypes(include=[np.number])
                if not numeric_data.empty:
                    selector = VarianceThreshold(threshold=threshold)
                    try:
                        selector.fit(numeric_data.fillna(0))
                        cols_to_keep = numeric_data.columns[selector.get_support()].tolist()
                        cols_to_drop = [c for c in numeric_data.columns if c not in cols_to_keep]

                        result_df = result_df.drop(columns=cols_to_drop, errors="ignore")

                        applied_steps.append(
                            {
                                "step": step_name,
                                "kind": kind,
                                "action": f"Dropped {len(cols_to_drop)} low-variance features",
                            }
                        )
                    except Exception:
                        applied_steps.append(
                            {
                                "step": step_name,
                                "kind": kind,
                                "action": "Variance threshold skipped (insufficient data)",
                            }
                        )

            # PCA
            elif kind == TransformKind.PCA:
                n_components = params.get("n_components", 10)

                numeric_data = result_df.select_dtypes(include=[np.number])
                if not numeric_data.empty and len(numeric_data.columns) > n_components:
                    pca = PCA(n_components=n_components)
                    try:
                        pca_features = pca.fit_transform(numeric_data.fillna(0))

                        # Replace with PCA components
                        result_df = result_df.drop(columns=numeric_data.columns)
                        for i in range(n_components):
                            feat = f"pca_{i}"
                            result_df[feat] = pca_features[:, i]
                            new_features.append(feat)

                        applied_steps.append(
                            {
                                "step": step_name,
                                "kind": kind,
                                "action": f"PCA reduced {len(numeric_data.columns)} -> {n_components} features",
                                "new_features": new_features,
                                "explained_variance": float(pca.explained_variance_ratio_.sum()),
                            }
                        )
                    except Exception:
                        applied_steps.append(
                            {
                                "step": step_name,
                                "kind": kind,
                                "action": "PCA skipped (insufficient data)",
                            }
                        )

        except Exception as e:
            applied_steps.append(
                {
                    "step": step_name,
                    "kind": kind,
                    "action": f"Failed: {str(e)}",
                    "error": True,
                }
            )

        all_new_features.extend(new_features)

    # Calculate feature scores for final features
    numeric_features = result_df.select_dtypes(include=[np.number]).columns.tolist()
    for col in numeric_features[:100]:  # Limit to 100 features
        feature_scores[col] = feature_quality_scores(result_df[col])

    # Generate validation report
    final_validation = validate_features(result_df)

    report = {
        "applied_steps": applied_steps,
        "feature_scores": feature_scores,
        "validation": final_validation,
        "summary": {
            "total_steps": len(steps),
            "applied_steps": len(applied_steps),
            "original_features": len(df.columns),
            "final_features": len(result_df.columns),
            "new_features_created": len(all_new_features),
        },
    }

    return result_df, report


def run_feature_engineering(
    df: pd.DataFrame,
    profile: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run complete feature engineering pipeline.

    Args:
        df: Input DataFrame
        profile: Optional data profile
        config: Optional configuration

    Returns:
        Dictionary with pipeline, report, graph, recommendations, summary, preview_columns, matrix_shape
    """
    # Build pipeline
    pipeline = build_feature_pipeline(df, profile, config)

    # Apply pipeline
    matrix_df, report = apply_pipeline(df, pipeline["steps"])

    # Generate visualizations
    visualizations: dict[str, Any] = {}

    # Correlation matrix
    numeric_data = matrix_df.select_dtypes(include=[np.number])
    if not numeric_data.empty and len(numeric_data.columns) <= 50:
        corr_matrix = numeric_data.corr()
        visualizations["correlation_matrix"] = {
            "type": "heatmap",
            "data": corr_matrix.to_dict(),
            "shape": corr_matrix.shape,
        }

    # PCA plot (if applicable)
    if len(numeric_data.columns) >= 2:
        try:
            pca = PCA(n_components=2)
            pca_result = pca.fit_transform(numeric_data.fillna(0).iloc[:1000])
            visualizations["pca_plot"] = {
                "type": "scatter",
                "data": {
                    "pc1": pca_result[:, 0].tolist(),
                    "pc2": pca_result[:, 1].tolist(),
                },
                "explained_variance": pca.explained_variance_ratio_.tolist(),
            }
        except Exception:
            pass

    # Variance distribution
    if not numeric_data.empty:
        variances = numeric_data.var().sort_values(ascending=False)
        visualizations["variance_distribution"] = {
            "type": "bar",
            "data": variances.head(20).to_dict(),
        }

    # Feature importance placeholder
    visualizations["feature_importance_placeholder"] = {
        "type": "bar",
        "disabled": True,
        "reason": "Requires Phase 7 model training",
        "data": {},
    }

    # Generate recommendations
    recommendations = []

    if report["validation"]["drop_candidates"]["high_correlation"]:
        recommendations.append(
            {
                "type": "warning",
                "message": f"Found {len(report['validation']['drop_candidates']['high_correlation'])} "
                "highly correlated features. Consider removing for model efficiency.",
            }
        )

    if len(matrix_df.columns) > 100:
        recommendations.append(
            {
                "type": "info",
                "message": f"Generated {len(matrix_df.columns)} features. "
                "Consider dimensionality reduction (PCA/selection) for better performance.",
            }
        )

    if pipeline.get("disabled_steps"):
        recommendations.append(
            {
                "type": "info",
                "message": f"{len(pipeline['disabled_steps'])} advanced transforms disabled. "
                "Enable in Phase 7 with target-aware methods.",
            }
        )

    # Calculate usefulness estimate
    usefulness_score = estimate_usefulness(report)

    return {
        "pipeline": pipeline,
        "report": report,
        "visualizations": visualizations,
        "recommendations": recommendations,
        "summary": {
            "input_shape": df.shape,
            "output_shape": matrix_df.shape,
            "features_created": len(matrix_df.columns) - len(df.columns),
            "usefulness_score": usefulness_score,
            "quality_issues": len(report["validation"]["issues"]),
        },
        "preview_columns": matrix_df.columns.tolist()[:50],
        "matrix_shape": matrix_df.shape,
        "matrix_sample": matrix_df.head(5).to_dict(),
    }


def estimate_usefulness(report: dict[str, Any]) -> float:
    """Estimate usefulness score from feature engineering report.

    Args:
        report: Feature engineering report

    Returns:
        Usefulness score (0-100)
    """
    summary = report.get("summary", {})
    validation = report.get("validation", {})
    feature_scores = report.get("feature_scores", {})

    # Base score from feature creation
    original = summary.get("original_features", 1)
    final = summary.get("final_features", 1)
    creation_ratio = final / original
    creation_score = min(30, creation_ratio * 10)

    # Quality score from feature scores
    if feature_scores:
        avg_quality = np.mean([fs.get("overall_score", 0) for fs in feature_scores.values()])
        quality_score = avg_quality * 0.4  # Scale to 40 points
    else:
        quality_score = 20

    # Deduct for issues
    issues_count = len(validation.get("issues", []))
    issue_penalty = min(20, issues_count * 2)

    # Bonus for diverse transformations
    applied_steps = report.get("applied_steps", [])
    diversity_score = min(20, len(applied_steps) * 2)

    total_score = creation_score + quality_score + diversity_score - issue_penalty
    return float(max(0.0, min(100.0, float(total_score))))


def memory_safe_sample(
    df: pd.DataFrame,
    max_rows: int = 200000,
) -> pd.DataFrame:
    """Sample DataFrame if it exceeds memory threshold.

    Args:
        df: Input DataFrame
        max_rows: Maximum rows to keep

    Returns:
        Sampled DataFrame
    """
    if len(df) <= max_rows:
        return df

    # Sample with stratification if possible
    sample_size = min(max_rows, len(df))
    return df.sample(n=sample_size, random_state=42)


def streaming_chunk_size(
    n_rows: int,
    n_cols: int,
) -> int:
    """Calculate optimal chunk size for streaming operations.

    Args:
        n_rows: Number of rows
        n_cols: Number of columns

    Returns:
        Optimal chunk size
    """
    # Estimate memory per row (bytes)
    bytes_per_row = n_cols * 8  # Assume 8 bytes per numeric value

    # Target 100MB chunks
    target_bytes = 100 * 1024 * 1024
    chunk_size = target_bytes // bytes_per_row

    # Clamp between 1000 and 50000
    return max(1000, min(50000, chunk_size))

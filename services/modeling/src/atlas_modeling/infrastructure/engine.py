"""Deterministic training engine and algorithm adapters."""

from __future__ import annotations

import io
import pickle
import time
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier, DummyRegressor
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_absolute_percentage_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import GaussianNB
from sklearn.neighbors import KNeighborsClassifier, KNeighborsRegressor
from sklearn.svm import SVC, SVR
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

from atlas_modeling.domain import AlgorithmName, ProblemType


@dataclass
class TrainingOutcome:
    model: Any
    metrics: dict[str, Any]
    report: dict[str, Any]
    model_bytes: bytes
    training_seconds: float
    warnings: list[str]


def _problem_type(value: str) -> ProblemType:
    try:
        return ProblemType(value)
    except ValueError as exc:
        raise ValueError(f"unsupported problem type: {value}") from exc


def _is_classification(problem_type: ProblemType) -> bool:
    return problem_type in {
        ProblemType.BINARY_CLASSIFICATION,
        ProblemType.MULTICLASS_CLASSIFICATION,
    }


def _build_estimator(algorithm: str, problem_type: ProblemType, seed: int) -> Any:
    name = AlgorithmName(algorithm)
    cls = _is_classification(problem_type)
    if name is AlgorithmName.LOGISTIC_REGRESSION and cls:
        return LogisticRegression(max_iter=1000, random_state=seed)
    if name is AlgorithmName.LINEAR_REGRESSION and not cls:
        return LinearRegression()
    if name is AlgorithmName.DECISION_TREE:
        return (
            DecisionTreeClassifier(random_state=seed)
            if cls
            else DecisionTreeRegressor(random_state=seed)
        )
    if name is AlgorithmName.RANDOM_FOREST:
        return (
            RandomForestClassifier(random_state=seed)
            if cls
            else RandomForestRegressor(random_state=seed)
        )
    if name is AlgorithmName.EXTRA_TREES:
        return (
            ExtraTreesClassifier(random_state=seed)
            if cls
            else ExtraTreesRegressor(random_state=seed)
        )
    if name is AlgorithmName.KNN:
        return KNeighborsClassifier() if cls else KNeighborsRegressor()
    if name is AlgorithmName.NAIVE_BAYES and cls:
        return GaussianNB()
    if name is AlgorithmName.SVM:
        return SVC(probability=True, random_state=seed) if cls else SVR()
    if name is AlgorithmName.DUMMY_BASELINE:
        return DummyClassifier(strategy="most_frequent") if cls else DummyRegressor(strategy="mean")

    if name is AlgorithmName.XGBOOST:
        try:
            from xgboost import XGBClassifier, XGBRegressor  # type: ignore[import-not-found]

            return (
                XGBClassifier(random_state=seed, n_estimators=100)
                if cls
                else XGBRegressor(random_state=seed, n_estimators=100)
            )
        except Exception as exc:  # noqa: BLE001
            raise ValueError("xgboost is not installed") from exc

    if name is AlgorithmName.LIGHTGBM:
        raise ValueError("lightgbm adapter is optional and not installed")
    if name is AlgorithmName.CATBOOST:
        raise ValueError("catboost adapter is optional and not installed")
    raise ValueError(f"algorithm {algorithm} is not supported for {problem_type.value}")


def _default_algorithm(problem_type: ProblemType) -> AlgorithmName:
    if _is_classification(problem_type):
        return AlgorithmName.LOGISTIC_REGRESSION
    return AlgorithmName.LINEAR_REGRESSION


def _classification_metrics(
    y_true: pd.Series, y_pred: np.ndarray, y_score: np.ndarray | None
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, average="weighted", zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, average="weighted", zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
    if y_score is not None:
        try:
            if y_score.ndim == 1:
                out["roc_auc"] = float(roc_auc_score(y_true, y_score))
            else:
                out["roc_auc"] = float(
                    roc_auc_score(y_true, y_score, multi_class="ovr", average="weighted")
                )
        except Exception:  # noqa: BLE001
            out["roc_auc"] = None
    else:
        out["roc_auc"] = None
    return out


def _regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, Any]:
    residuals = y_true.to_numpy() - y_pred
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mse": float(mean_squared_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "r2": float(r2_score(y_true, y_pred)),
        "mape": float(mean_absolute_percentage_error(y_true, y_pred)),
        "residual_stats": {
            "mean": float(np.mean(residuals)),
            "std": float(np.std(residuals)),
            "min": float(np.min(residuals)),
            "max": float(np.max(residuals)),
        },
    }


def run_training(
    df: pd.DataFrame,
    *,
    target_column: str,
    problem_type_value: str,
    config: dict[str, Any] | None = None,
) -> TrainingOutcome:
    config = config or {}
    if target_column not in df.columns:
        raise ValueError(f"target column {target_column} not in feature matrix")

    problem_type = _problem_type(problem_type_value)
    seed = int(config.get("random_seed", 42))
    validation_size = float(config.get("validation_size", 0.2))
    shuffle = bool(config.get("shuffle", True))
    stratify = bool(config.get("stratify", _is_classification(problem_type)))
    algorithm = str(config.get("algorithm") or _default_algorithm(problem_type).value)

    y = df[target_column]
    x = df.drop(columns=[target_column]).copy()
    x = pd.get_dummies(x, drop_first=False)
    x = x.fillna(0)

    y_for_split = y if (_is_classification(problem_type) and stratify) else None
    x_train, x_val, y_train, y_val = train_test_split(
        x,
        y,
        test_size=validation_size,
        random_state=seed,
        shuffle=shuffle,
        stratify=y_for_split,
    )

    model = _build_estimator(algorithm, problem_type, seed)
    started = time.perf_counter()
    model.fit(x_train, y_train)
    elapsed = time.perf_counter() - started
    y_pred = model.predict(x_val)

    y_score: np.ndarray | None = None
    if _is_classification(problem_type):
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(x_val)
            y_score = proba[:, 1] if proba.ndim == 2 and proba.shape[1] == 2 else proba
        elif hasattr(model, "decision_function"):
            y_score = model.decision_function(x_val)
        metrics = _classification_metrics(y_val, y_pred, y_score)
    else:
        metrics = _regression_metrics(y_val, y_pred)

    buffer = io.BytesIO()
    pickle.dump(model, buffer)
    model_bytes = buffer.getvalue()

    warnings: list[str] = []
    if config.get("cross_validation"):
        warnings.append("cross_validation is a placeholder in phase 7")
    if config.get("normalize"):
        warnings.append("normalize is a placeholder in phase 7")

    report = {
        "problem_type": problem_type.value,
        "algorithm": algorithm,
        "target_column": target_column,
        "split": {
            "train_rows": int(len(x_train)),
            "validation_rows": int(len(x_val)),
            "validation_size": validation_size,
            "shuffle": shuffle,
            "stratify": stratify,
            "random_seed": seed,
        },
        "feature_schema": {
            "input_columns": [str(c) for c in df.columns],
            "model_columns": [str(c) for c in x.columns],
            "feature_count": int(x.shape[1]),
        },
        "metrics": metrics,
        "warnings": warnings,
    }

    return TrainingOutcome(
        model=model,
        metrics=metrics,
        report=report,
        model_bytes=model_bytes,
        training_seconds=elapsed,
        warnings=warnings,
    )

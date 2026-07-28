"""Optuna-first HPO engine for Phase 8."""

from __future__ import annotations

import io
import math
import time
from dataclasses import dataclass
from typing import Any

import optuna
import pandas as pd
from atlas_hpo.domain import MAXIMIZE_OBJECTIVES, MetricObjective, OptimizerName, TrialStatus
from atlas_modeling.infrastructure.engine import run_training
from optuna.pruners import MedianPruner, NopPruner
from optuna.samplers import GridSampler, RandomSampler, TPESampler


@dataclass
class TrialResult:
    trial_number: int
    status: str
    objective_value: float | None
    params: dict[str, Any]
    metrics: dict[str, Any]
    report: dict[str, Any]
    training_seconds: float


@dataclass
class StudyRunResult:
    study_name: str
    optimizer: str
    direction: str
    search_space: dict[str, Any]
    trials: list[TrialResult]
    best_params: dict[str, Any]
    best_value: float | None
    best_metrics: dict[str, Any]
    best_report: dict[str, Any]
    summary: dict[str, Any]


def build_search_space(algorithm: str, problem_type: str) -> dict[str, dict[str, Any]]:
    algorithm = algorithm.lower()
    if algorithm == "random_forest":
        return {
            "n_estimators": {"kind": "int", "low": 50, "high": 300, "step": 25},
            "max_depth": {"kind": "int", "low": 2, "high": 20},
            "min_samples_split": {"kind": "int", "low": 2, "high": 10},
            "min_samples_leaf": {"kind": "int", "low": 1, "high": 5},
            "bootstrap": {"kind": "bool"},
        }
    if algorithm == "decision_tree":
        return {
            "criterion": {
                "kind": "categorical",
                "choices": ["gini", "entropy"] if "classification" in problem_type else ["squared_error"],
            },
            "splitter": {"kind": "categorical", "choices": ["best", "random"]},
            "max_depth": {"kind": "int", "low": 2, "high": 20},
            "min_samples_split": {"kind": "int", "low": 2, "high": 10},
            "min_samples_leaf": {"kind": "int", "low": 1, "high": 5},
        }
    if algorithm == "svm":
        return {
            "C": {"kind": "log_uniform", "low": 1e-3, "high": 100.0},
            "kernel": {"kind": "categorical", "choices": ["rbf", "linear", "poly"]},
            "gamma": {"kind": "categorical", "choices": ["scale", "auto"]},
        }
    if algorithm == "knn":
        return {
            "n_neighbors": {"kind": "int", "low": 3, "high": 21, "step": 2},
            "weights": {"kind": "categorical", "choices": ["uniform", "distance"]},
            "p": {"kind": "categorical", "choices": [1, 2]},
        }
    if algorithm == "extra_trees":
        return {
            "n_estimators": {"kind": "int", "low": 50, "high": 300, "step": 25},
            "max_depth": {"kind": "int", "low": 2, "high": 20},
            "min_samples_split": {"kind": "int", "low": 2, "high": 10},
            "min_samples_leaf": {"kind": "int", "low": 1, "high": 5},
        }
    if algorithm == "logistic_regression":
        return {
            "C": {"kind": "log_uniform", "low": 1e-3, "high": 100.0},
            "solver": {"kind": "categorical", "choices": ["lbfgs", "liblinear"]},
        }
    if algorithm == "linear_regression":
        return {"fit_intercept": {"kind": "bool"}}
    return {}


def _sample_param(trial: optuna.Trial, name: str, spec: dict[str, Any]) -> Any:
    kind = spec["kind"]
    if kind == "int":
        return trial.suggest_int(name, int(spec["low"]), int(spec["high"]), step=int(spec.get("step", 1)))
    if kind == "float":
        return trial.suggest_float(name, float(spec["low"]), float(spec["high"]))
    if kind == "uniform":
        return trial.suggest_float(name, float(spec["low"]), float(spec["high"]))
    if kind == "log_uniform":
        return trial.suggest_float(name, float(spec["low"]), float(spec["high"]), log=True)
    if kind == "discrete_uniform":
        return trial.suggest_float(name, float(spec["low"]), float(spec["high"]), step=float(spec["step"]))
    if kind == "categorical":
        return trial.suggest_categorical(name, list(spec["choices"]))
    if kind == "bool":
        return trial.suggest_categorical(name, [True, False])
    raise ValueError(f"unsupported search space kind: {kind}")


def _expand_grid(search_space: dict[str, dict[str, Any]]) -> dict[str, list[Any]]:
    expanded: dict[str, list[Any]] = {}
    for name, spec in search_space.items():
        kind = spec["kind"]
        if kind == "int":
            step = int(spec.get("step", 1))
            expanded[name] = list(range(int(spec["low"]), int(spec["high"]) + 1, step))
        elif kind in {"float", "uniform"}:
            low = float(spec["low"])
            high = float(spec["high"])
            expanded[name] = [low, (low + high) / 2, high]
        elif kind == "log_uniform":
            low = float(spec["low"])
            high = float(spec["high"])
            expanded[name] = [low, math.sqrt(low * high), high]
        elif kind == "discrete_uniform":
            low = float(spec["low"])
            high = float(spec["high"])
            step_value = float(spec["step"])
            values: list[Any] = []
            current = low
            while current <= high + 1e-9:
                values.append(round(current, 10))
                current += step_value
            expanded[name] = values
        elif kind == "categorical":
            expanded[name] = list(spec["choices"])
        elif kind == "bool":
            expanded[name] = [True, False]
        else:
            raise ValueError(f"unsupported grid kind: {kind}")
    return expanded


def _direction(metric_objective: MetricObjective) -> str:
    return "maximize" if metric_objective in MAXIMIZE_OBJECTIVES else "minimize"


def _sampler(name: OptimizerName, search_space: dict[str, dict[str, Any]], seed: int) -> optuna.samplers.BaseSampler:
    if name is OptimizerName.RANDOM:
        return RandomSampler(seed=seed)
    if name is OptimizerName.GRID:
        return GridSampler(_expand_grid(search_space))
    if name is OptimizerName.TPE:
        return TPESampler(seed=seed)
    if name is OptimizerName.CMA_ES:
        return RandomSampler(seed=seed)
    if name is OptimizerName.NSGA_II:
        return TPESampler(seed=seed)
    return TPESampler(seed=seed)


def _pruner(config: dict[str, Any]) -> optuna.pruners.BasePruner:
    if not bool(config.get("trial_pruning", True)):
        return NopPruner()
    return MedianPruner(n_startup_trials=int(config.get("pruner_warmup_trials", 3)))


def _objective_value(metrics: dict[str, Any], objective: MetricObjective) -> float:
    raw = metrics.get(objective.value)
    if raw is None:
        raise ValueError(f"objective metric {objective.value} missing from metrics")
    return float(raw)


def run_optimization(
    df: pd.DataFrame,
    *,
    target_column: str,
    problem_type: str,
    algorithm: str,
    optimizer: str,
    metric_objective: str,
    budget: dict[str, Any],
    base_config: dict[str, Any],
) -> StudyRunResult:
    optimizer_name = OptimizerName(optimizer)
    objective = MetricObjective(metric_objective)
    seed = int(base_config.get("random_seed", 42))
    search_space = build_search_space(algorithm, problem_type)
    direction = _direction(objective)
    max_trials = int(budget.get("max_trials", 10))
    timeout = budget.get("max_duration_seconds")
    max_duration_seconds = int(timeout) if timeout else None
    n_jobs = int(budget.get("parallel_workers", 1))
    study_name = f"hpo_{algorithm}_{seed}"
    study = optuna.create_study(
        study_name=study_name,
        direction=direction,
        sampler=_sampler(optimizer_name, search_space, seed),
        pruner=_pruner(base_config),
    )
    started = time.perf_counter()
    trial_results: list[TrialResult] = []
    best_metrics: dict[str, Any] = {}
    best_report: dict[str, Any] = {}

    def objective_fn(trial: optuna.Trial) -> float:
        params = {name: _sample_param(trial, name, spec) for name, spec in search_space.items()}
        config = dict(base_config)
        config["algorithm"] = algorithm
        config.update(params)
        t0 = time.perf_counter()
        outcome = run_training(
            df,
            target_column=target_column,
            problem_type_value=problem_type,
            config=config,
        )
        elapsed = time.perf_counter() - t0
        value = _objective_value(outcome.metrics, objective)
        trial.report(value, step=0)
        if trial.should_prune():
            trial_results.append(
                TrialResult(
                    trial_number=trial.number,
                    status=TrialStatus.PRUNED.value,
                    objective_value=value,
                    params=params,
                    metrics=outcome.metrics,
                    report=outcome.report,
                    training_seconds=elapsed,
                )
            )
            raise optuna.TrialPruned()

        trial.set_user_attr("report", outcome.report)
        trial.set_user_attr("metrics", outcome.metrics)
        trial.set_user_attr("training_seconds", elapsed)
        trial_results.append(
            TrialResult(
                trial_number=trial.number,
                status=TrialStatus.COMPLETED.value,
                objective_value=value,
                params=params,
                metrics=outcome.metrics,
                report=outcome.report,
                training_seconds=elapsed,
            )
        )
        return value

    study.optimize(
        objective_fn,
        n_trials=max_trials if optimizer_name is not OptimizerName.GRID else None,
        timeout=max_duration_seconds,
        n_jobs=max(1, n_jobs),
        catch=(ValueError,),
    )

    for frozen in study.trials:
        if frozen.state.is_finished() and frozen.state.name == "FAIL":
            trial_results.append(
                TrialResult(
                    trial_number=frozen.number,
                    status=TrialStatus.FAILED.value,
                    objective_value=frozen.value,
                    params=dict(frozen.params),
                    metrics={},
                    report={},
                    training_seconds=0.0,
                )
            )

    if study.best_trial is not None:
        best_metrics = dict(study.best_trial.user_attrs.get("metrics", {}))
        best_report = dict(study.best_trial.user_attrs.get("report", {}))

    duration = time.perf_counter() - started
    completed_trials = len([t for t in trial_results if t.status == TrialStatus.COMPLETED.value])
    pruned_trials = len([t for t in trial_results if t.status == TrialStatus.PRUNED.value])
    history = [
        {
            "trial_number": t.trial_number,
            "status": t.status,
            "objective_value": t.objective_value,
            "params": t.params,
            "metrics": t.metrics,
            "duration_seconds": t.training_seconds,
        }
        for t in sorted(trial_results, key=lambda item: item.trial_number)
    ]
    summary = {
        "study_name": study_name,
        "optimizer": optimizer_name.value,
        "direction": direction,
        "max_trials": max_trials,
        "duration_seconds": duration,
        "completed_trials": completed_trials,
        "pruned_trials": pruned_trials,
        "trials_per_second": completed_trials / duration if duration > 0 else 0.0,
        "average_trial_duration": (
            sum(t.training_seconds for t in trial_results if t.training_seconds) / max(1, completed_trials)
        ),
        "visualizations": {
            "optimization_history": history,
            "objective_curve": history,
            "trial_scatter": history,
            "timeline": history,
            "parameter_importance": {"placeholder": True},
            "parallel_coordinate": {"placeholder": True},
            "slice_plot": {"placeholder": True},
            "contour_plot": {"placeholder": True},
        },
        "parallel_execution": {
            "mode": "parallel_optuna_workers" if n_jobs > 1 else "sequential",
            "workers": n_jobs,
            "celery_workers": True,
            "ray_placeholder": True,
        },
        "early_stopping": {
            "trial_pruning": bool(base_config.get("trial_pruning", True)),
            "median_pruning": True,
            "successive_halving": "placeholder",
            "max_trials": max_trials,
            "max_duration_seconds": max_duration_seconds,
        },
    }

    return StudyRunResult(
        study_name=study_name,
        optimizer=optimizer_name.value,
        direction=direction,
        search_space=search_space,
        trials=history_to_trials(history),
        best_params=dict(study.best_params),
        best_value=study.best_value if len(study.trials) else None,
        best_metrics=best_metrics,
        best_report=best_report,
        summary=summary,
    )


def history_to_trials(history: list[dict[str, Any]]) -> list[TrialResult]:
    return [
        TrialResult(
            trial_number=int(item["trial_number"]),
            status=str(item["status"]),
            objective_value=(float(item["objective_value"]) if item["objective_value"] is not None else None),
            params=dict(item["params"]),
            metrics=dict(item["metrics"]),
            report={},
            training_seconds=float(item["duration_seconds"]),
        )
        for item in history
    ]


def trials_csv(rows: list[TrialResult]) -> bytes:
    frame = pd.DataFrame(
        [
            {
                "trial_number": row.trial_number,
                "status": row.status,
                "objective_value": row.objective_value,
                "params": row.params,
                "metrics": row.metrics,
                "duration_seconds": row.training_seconds,
            }
            for row in rows
        ]
    )
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")

"""Domain enums for the HPO bounded context."""

from __future__ import annotations

from enum import StrEnum


class OptimizationJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class StudyStatus(StrEnum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"


class TrialStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    PRUNED = "pruned"
    FAILED = "failed"


class OptimizerName(StrEnum):
    OPTUNA = "optuna"
    RANDOM = "random"
    GRID = "grid"
    TPE = "tpe"
    CMA_ES = "cma_es"
    NSGA_II = "nsga_ii"


class MetricObjective(StrEnum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    ROC_AUC = "roc_auc"
    BALANCED_ACCURACY = "balanced_accuracy"
    MAE = "mae"
    RMSE = "rmse"
    R2 = "r2"
    MAPE = "mape"


MAXIMIZE_OBJECTIVES = {
    MetricObjective.ACCURACY,
    MetricObjective.PRECISION,
    MetricObjective.RECALL,
    MetricObjective.F1,
    MetricObjective.ROC_AUC,
    MetricObjective.BALANCED_ACCURACY,
    MetricObjective.R2,
}


MINIMIZE_OBJECTIVES = {
    MetricObjective.MAE,
    MetricObjective.RMSE,
    MetricObjective.MAPE,
}

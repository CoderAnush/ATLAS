"""Feature store domain enums and constants."""

from __future__ import annotations

from enum import StrEnum


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    COMPLETED = "completed"
    FAILED = "failed"
    REJECTED = "rejected"


class FeatureSetStatus(StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    MATERIALIZED = "materialized"


class FeatureKind(StrEnum):
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    TEXT = "text"
    DATETIME = "datetime"
    INTERACTION = "interaction"
    POLYNOMIAL = "polynomial"
    RATIO = "ratio"
    DIFFERENCE = "difference"
    TRANSFORM = "transform"
    BINNING = "binning"
    TIME = "time"
    ENCODED = "encoded"
    SCALED = "scaled"
    REDUCED = "reduced"
    DERIVED = "derived"


class TransformKind(StrEnum):
    INTERACTION = "interaction"
    POLYNOMIAL = "polynomial"
    RATIO = "ratio"
    DIFFERENCE = "difference"
    LOG = "log"
    SQRT = "sqrt"
    POWER = "power"
    BINNING = "binning"
    TIME_PARTS = "time_parts"
    TEXT_STATS = "text_stats"
    TFIDF = "tfidf"
    BAG_OF_WORDS = "bag_of_words"
    HASHING = "hashing"
    NGRAMS = "ngrams"
    EMBEDDING = "embedding_placeholder"
    ONE_HOT = "one_hot"
    ORDINAL = "ordinal"
    FREQUENCY = "frequency"
    COUNT = "count"
    BINARY = "binary"
    TARGET_ENCODING = "target_encoding_placeholder"
    STANDARD_SCALE = "standard_scale"
    MINMAX_SCALE = "minmax_scale"
    ROBUST_SCALE = "robust_scale"
    MAXABS_SCALE = "maxabs_scale"
    QUANTILE = "quantile"
    POWER_TRANSFORM = "power_transform"
    VARIANCE_THRESHOLD = "variance_threshold"
    CORRELATION_THRESHOLD = "correlation_threshold"
    MUTUAL_INFO = "mutual_info_placeholder"
    CHI2 = "chi2_placeholder"
    ANOVA = "anova_placeholder"
    RFE = "rfe_placeholder"
    FEATURE_IMPORTANCE = "feature_importance_placeholder"
    PCA = "pca"
    TRUNCATED_SVD = "truncated_svd"
    FEATURE_AGGLOMERATION = "feature_agglomeration"
    UMAP = "umap_placeholder"
    DROP_CONSTANT = "drop_constant"
    DROP_DUPLICATE = "drop_duplicate"
    DROP_HIGH_CORR = "drop_high_corr"
    DROP_SPARSE = "drop_sparse"
    DROP_LEAKY = "drop_leaky"
    DROP_NEAR_CONSTANT = "drop_near_constant"
    PASSTHROUGH = "passthrough"


LEAKY_NAME_HINTS = frozenset(
    {
        "id",
        "uuid",
        "guid",
        "ssn",
        "password",
        "token",
        "secret",
        "future_",
        "label_encoded",
    }
)

HOLIDAY_MONTH_DAYS = frozenset(
    {
        (1, 1),
        (7, 4),
        (12, 25),
        (12, 31),
    }
)

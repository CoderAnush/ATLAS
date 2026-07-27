"""Feature store application layer exports."""

from atlas_feature_store.application.agent import AGENT_NAME
from atlas_feature_store.application.service import FeatureStoreService

__all__ = [
    "AGENT_NAME",
    "FeatureStoreService",
]

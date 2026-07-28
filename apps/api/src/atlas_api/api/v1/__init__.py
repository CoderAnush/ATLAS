"""Versioned API routers."""

from atlas_api.api.v1.health import router as health_router
from atlas_catalog.api import build_catalog_router
from atlas_feature_store.api import build_feature_store_router
from atlas_hpo.api import build_hpo_router
from atlas_identity.api import build_identity_router
from atlas_modeling.api import build_modeling_router
from atlas_preparation.api import build_preparation_router
from atlas_profiling.api import build_profiling_router
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(build_identity_router())
api_v1_router.include_router(build_catalog_router())
api_v1_router.include_router(build_profiling_router())
api_v1_router.include_router(build_preparation_router())
api_v1_router.include_router(build_feature_store_router())
api_v1_router.include_router(build_modeling_router())
api_v1_router.include_router(build_hpo_router())

root_health_router = health_router

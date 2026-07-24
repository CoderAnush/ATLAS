"""Versioned API routers."""

from atlas_api.api.v1.health import router as health_router
from atlas_catalog.api import build_catalog_router
from atlas_identity.api import build_identity_router
from fastapi import APIRouter

api_v1_router = APIRouter(prefix="/v1")
api_v1_router.include_router(health_router)
api_v1_router.include_router(build_identity_router())
api_v1_router.include_router(build_catalog_router())

root_health_router = health_router

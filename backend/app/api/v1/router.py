"""Aggregate router for all v1 endpoints."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    employees,
    employment_contracts,
    framework,
    health,
    meta,
    tenants,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(meta.router, tags=["meta"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(employees.router, prefix="/employees", tags=["employees"])
api_router.include_router(
    employment_contracts.router,
    prefix="/employment-contracts",
    tags=["employment-contracts"],
)
api_router.include_router(framework.router, prefix="/framework", tags=["framework"])

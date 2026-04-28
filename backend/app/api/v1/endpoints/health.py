"""Liveness and readiness probes.

- `/health`       — liveness, no external deps
- `/health/ready` — readiness, verifies DB connectivity
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.core.config import get_settings
from app.core.database import get_db

router = APIRouter()
settings = get_settings()


@router.get("/health", status_code=status.HTTP_200_OK)
async def health() -> dict[str, str]:
    """Liveness probe — always cheap, does not touch external services."""
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.app_env,
    }


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    """Readiness probe — verifies database connectivity."""
    await db.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}

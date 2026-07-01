"""Meta endpoints — non-domain information about the service."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__

router = APIRouter()


@router.get("/meta/version")
async def version() -> dict[str, str]:
    return {"version": __version__, "service": "payroll-futuristic-api"}


@router.get("/meta/milestone")
async def milestone() -> dict[str, str]:
    """Reflects the SOW milestone this build corresponds to."""
    return {
        "milestone": "3",
        "title": "Basic Payroll Engine",
        "period": "2026-06-01 / 2026-06-30",
        "status": "complete",
    }

"""Tenant resolution helpers."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payroll_framework import DEFAULT_TENANT, DEFAULT_TENANT_ID
from app.models.tenant import Tenant


async def get_or_create_default_tenant(db: AsyncSession) -> Tenant:
    tenant = await db.get(Tenant, DEFAULT_TENANT_ID)
    if tenant is not None:
        return tenant

    result = await db.execute(
        select(Tenant).where(Tenant.slug == DEFAULT_TENANT["slug"])
    )
    tenant = result.scalar_one_or_none()
    if tenant is not None:
        return tenant

    tenant = Tenant(**DEFAULT_TENANT)
    db.add(tenant)
    await db.flush()
    return tenant


async def resolve_tenant_id(db: AsyncSession, tenant_id: UUID | None) -> UUID:
    if tenant_id is None:
        return (await get_or_create_default_tenant(db)).id

    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return tenant.id

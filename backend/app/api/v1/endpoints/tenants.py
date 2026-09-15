"""Tenant endpoints."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.v1.pagination import PageLimit, PageOffset
from app.core.idempotency import (
    complete_idempotency_reservation,
    lookup_idempotency_key,
)
from app.core.rbac import AccessContext, require_permission
from app.models.tenant import Tenant
from app.schemas.tenant import TenantCreate, TenantRead

router = APIRouter()


@router.get("", response_model=list[TenantRead])
async def list_tenants(
    access: AccessContext = Depends(require_permission("tenants:manage")),
    limit: PageLimit = 100,
    offset: PageOffset = 0,
) -> list[TenantRead]:
    stmt = select(Tenant).order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
    result = await access.db.execute(stmt)
    return [TenantRead.model_validate(t) for t in result.scalars().all()]


@router.post("", response_model=TenantRead, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    request: Request,
    access: AccessContext = Depends(require_permission("tenants:manage")),
) -> TenantRead:
    db = access.db
    cached, reservation = await lookup_idempotency_key(
        db,
        request,
        payload,
        tenant_id=access.tenant_id,
    )
    if cached is not None:
        return TenantRead.model_validate(cached)

    tenant = Tenant(**payload.model_dump())
    db.add(tenant)
    try:
        await db.flush()
        await db.refresh(tenant)
        response = TenantRead.model_validate(tenant)

        if reservation is not None:
            complete_idempotency_reservation(
                reservation,
                response.model_dump(mode="json"),
                status_code=status.HTTP_201_CREATED,
            )
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tenant slug already exists",
        ) from exc
    return response


@router.get("/{tenant_id}", response_model=TenantRead)
async def get_tenant(
    tenant_id: UUID,
    access: AccessContext = Depends(require_permission("tenants:manage")),
) -> TenantRead:
    tenant = await access.db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )
    return TenantRead.model_validate(tenant)

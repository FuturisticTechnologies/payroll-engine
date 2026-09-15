"""Employment contract endpoints."""
from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError

from app.api.v1.pagination import PageLimit, PageOffset
from app.core.database import set_tenant_context
from app.core.idempotency import (
    complete_idempotency_reservation,
    lookup_idempotency_key,
)
from app.core.rbac import AccessContext, require_permission
from app.core.tenancy import resolve_tenant_id
from app.models.employee import Employee
from app.models.employment import EmploymentContract
from app.schemas.employment import EmploymentContractCreate, EmploymentContractRead

router = APIRouter()


async def _tenant_for_request(
    access: AccessContext,
    requested_tenant_id: UUID | None,
) -> UUID:
    tenant_id = requested_tenant_id or access.tenant_id
    if tenant_id != access.tenant_id and not access.user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied for requested tenant",
        )
    await set_tenant_context(
        access.db,
        tenant_id,
        is_superuser=access.user.is_superuser,
    )
    return await resolve_tenant_id(access.db, tenant_id)


async def _ensure_contract_window_is_unambiguous(
    access: AccessContext,
    payload: EmploymentContractCreate,
    tenant_id: UUID,
) -> None:
    db = access.db
    employee = await db.get(Employee, payload.employee_id)
    if employee is None or employee.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    requested_end = payload.effective_to or date.max
    overlap_stmt = (
        select(EmploymentContract.id)
        .where(
            EmploymentContract.employee_id == payload.employee_id,
            EmploymentContract.tenant_id == tenant_id,
            EmploymentContract.effective_from <= requested_end,
            or_(
                EmploymentContract.effective_to.is_(None),
                EmploymentContract.effective_to >= payload.effective_from,
            ),
        )
        .limit(1)
    )
    if (await db.execute(overlap_stmt)).scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employment contract overlaps an existing contract",
        )

    if payload.is_primary:
        primary_stmt = (
            select(EmploymentContract.id)
            .where(
                EmploymentContract.employee_id == payload.employee_id,
                EmploymentContract.tenant_id == tenant_id,
                EmploymentContract.is_primary.is_(True),
            )
            .limit(1)
        )
        if (await db.execute(primary_stmt)).scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Employee already has a primary employment contract",
            )


@router.get("", response_model=list[EmploymentContractRead])
async def list_contracts(
    access: AccessContext = Depends(require_permission("contracts:manage")),
    employee_id: UUID | None = None,
    tenant_id: UUID | None = None,
    limit: PageLimit = 100,
    offset: PageOffset = 0,
) -> list[EmploymentContractRead]:
    db = access.db
    resolved_tenant_id = await _tenant_for_request(access, tenant_id)
    stmt = select(EmploymentContract).where(
        EmploymentContract.tenant_id == resolved_tenant_id
    )
    if employee_id is not None:
        stmt = stmt.where(EmploymentContract.employee_id == employee_id)
    stmt = stmt.order_by(EmploymentContract.effective_from.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [EmploymentContractRead.model_validate(c) for c in result.scalars().all()]


@router.post("", response_model=EmploymentContractRead, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: EmploymentContractCreate,
    request: Request,
    access: AccessContext = Depends(require_permission("contracts:manage")),
) -> EmploymentContractRead:
    db = access.db
    tenant_id = await _tenant_for_request(access, payload.tenant_id)
    cached, reservation = await lookup_idempotency_key(
        db,
        request,
        payload,
        tenant_id=tenant_id,
    )
    if cached is not None:
        return EmploymentContractRead.model_validate(cached)

    await _ensure_contract_window_is_unambiguous(access, payload, tenant_id)

    data = payload.model_dump()
    data["tenant_id"] = tenant_id
    contract = EmploymentContract(**data)
    db.add(contract)
    try:
        await db.flush()
        await db.refresh(contract)
        response = EmploymentContractRead.model_validate(contract)

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
            detail="Employment contract already exists for this effective date",
        ) from exc
    return response


@router.get("/{contract_id}", response_model=EmploymentContractRead)
async def get_contract(
    contract_id: UUID,
    access: AccessContext = Depends(require_permission("contracts:manage")),
) -> EmploymentContractRead:
    contract = await access.db.get(EmploymentContract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employment contract not found",
        )
    return EmploymentContractRead.model_validate(contract)

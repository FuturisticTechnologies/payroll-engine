"""Employee endpoints."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import set_tenant_context
from app.core.idempotency import (
    complete_idempotency_reservation,
    lookup_idempotency_key,
)
from app.core.rbac import AccessContext, require_permission
from app.core.tenancy import resolve_tenant_id
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeRead

router = APIRouter()


def _employee_number() -> str:
    return f"EMP-{uuid4().hex[:8].upper()}"


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


@router.get("", response_model=list[EmployeeRead])
async def list_employees(
    access: AccessContext = Depends(require_permission("employees:read")),
    limit: int = 100,
    offset: int = 0,
    tenant_id: UUID | None = None,
) -> list[EmployeeRead]:
    db = access.db
    resolved_tenant_id = await _tenant_for_request(access, tenant_id)
    stmt = (
        select(Employee)
        .where(Employee.tenant_id == resolved_tenant_id)
        .order_by(Employee.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return [EmployeeRead.model_validate(e) for e in result.scalars().all()]


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    request: Request,
    access: AccessContext = Depends(require_permission("employees:write")),
) -> EmployeeRead:
    db = access.db
    data = payload.model_dump()
    tenant_id = await _tenant_for_request(access, data["tenant_id"])
    cached, reservation = await lookup_idempotency_key(
        db,
        request,
        payload,
        tenant_id=tenant_id,
    )
    if cached is not None:
        return EmployeeRead.model_validate(cached)

    data.pop("tenant_id")
    employee_number = data.pop("employee_number") or _employee_number()
    employee = Employee(
        **data,
        tenant_id=tenant_id,
        employee_number=employee_number,
    )
    db.add(employee)
    try:
        await db.flush()
        await db.refresh(employee)
        response = EmployeeRead.model_validate(employee)

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
            detail="Employee already exists for this tenant",
        ) from exc
    return response


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: UUID,
    access: AccessContext = Depends(require_permission("employees:read")),
) -> EmployeeRead:
    employee = await access.db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
    return EmployeeRead.model_validate(employee)

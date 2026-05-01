"""Employee endpoints — scaffold.

Only list/create are implemented in Milestone 1 to prove the data model
and session dependency wiring end-to-end. Payroll-bearing fields arrive in
later milestones alongside PAYE, NI and statutory payment logic.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.employee import Employee
from app.schemas.employee import EmployeeCreate, EmployeeRead

router = APIRouter()


@router.get("", response_model=list[EmployeeRead])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
) -> list[EmployeeRead]:
    stmt = select(Employee).order_by(Employee.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(stmt)
    return [EmployeeRead.model_validate(e) for e in result.scalars().all()]


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
async def create_employee(
    payload: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
) -> EmployeeRead:
    employee = Employee(**payload.model_dump())
    db.add(employee)
    await db.commit()
    await db.refresh(employee)
    return EmployeeRead.model_validate(employee)


@router.get("/{employee_id}", response_model=EmployeeRead)
async def get_employee(
    employee_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> EmployeeRead:
    employee = await db.get(Employee, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )
    return EmployeeRead.model_validate(employee)

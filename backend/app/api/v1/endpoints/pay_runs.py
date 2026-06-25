"""Milestone 3 payroll run endpoints."""
from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import set_tenant_context
from app.core.idempotency import (
    complete_idempotency_reservation,
    lookup_idempotency_key,
)
from app.core.payroll_engine import calculate_and_persist_pay_run
from app.core.rbac import AccessContext, require_permission
from app.core.tenancy import resolve_tenant_id
from app.models.payroll import (
    PayPeriod,
    PayrollLedgerEntry,
    PayrollLineItem,
    PayrollRun,
    PayrollRunLine,
)
from app.schemas.payroll import (
    PayPeriodRead,
    PayrollLedgerEntryRead,
    PayrollLineItemRead,
    PayrollRunLineRead,
    PayRunCreate,
    PayRunRead,
    PayRunSummaryRead,
)

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


@router.get("", response_model=list[PayRunSummaryRead])
async def list_pay_runs(
    access: AccessContext = Depends(require_permission("payroll:read")),
    tenant_id: UUID | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[PayRunSummaryRead]:
    resolved_tenant_id = await _tenant_for_request(access, tenant_id)
    stmt = (
        select(PayrollRun)
        .where(PayrollRun.tenant_id == resolved_tenant_id)
        .order_by(PayrollRun.calculated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await access.db.execute(stmt)
    return [PayRunSummaryRead.model_validate(run) for run in result.scalars().all()]


@router.post("", response_model=PayRunRead, status_code=status.HTTP_201_CREATED)
async def create_pay_run(
    payload: PayRunCreate,
    request: Request,
    access: AccessContext = Depends(require_permission("payroll:run")),
) -> PayRunRead:
    db = access.db
    tenant_id = await _tenant_for_request(access, payload.tenant_id)
    cached, reservation = await lookup_idempotency_key(
        db,
        request,
        payload,
        tenant_id=tenant_id,
    )
    if cached is not None:
        return PayRunRead.model_validate(cached)

    try:
        pay_run = await calculate_and_persist_pay_run(
            db,
            tenant_id,
            payload,
            created_by_user_id=access.user.id,
        )
        response = await _pay_run_read(db, pay_run)
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
            detail="Payroll run already exists for this pay period",
        ) from exc
    return response


@router.get("/{pay_run_id}", response_model=PayRunRead)
async def get_pay_run(
    pay_run_id: UUID,
    access: AccessContext = Depends(require_permission("payroll:read")),
) -> PayRunRead:
    pay_run = await access.db.get(PayrollRun, pay_run_id)
    if pay_run is None or (
        pay_run.tenant_id != access.tenant_id and not access.user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )
    return await _pay_run_read(access.db, pay_run)


@router.get("/{pay_run_id}/ledger", response_model=list[PayrollLedgerEntryRead])
async def get_pay_run_ledger(
    pay_run_id: UUID,
    access: AccessContext = Depends(require_permission("payroll:read")),
) -> list[PayrollLedgerEntryRead]:
    pay_run = await access.db.get(PayrollRun, pay_run_id)
    if pay_run is None or (
        pay_run.tenant_id != access.tenant_id and not access.user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )
    result = await access.db.execute(
        select(PayrollLedgerEntry)
        .where(PayrollLedgerEntry.pay_run_id == pay_run.id)
        .order_by(PayrollLedgerEntry.sequence_number)
    )
    return [
        PayrollLedgerEntryRead.model_validate(entry)
        for entry in result.scalars().all()
    ]


async def _pay_run_read(db, pay_run: PayrollRun) -> PayRunRead:  # type: ignore[no-untyped-def]
    period = await db.get(PayPeriod, pay_run.pay_period_id)
    if period is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Payroll run is missing its pay period",
        )

    lines_result = await db.execute(
        select(PayrollRunLine)
        .where(PayrollRunLine.pay_run_id == pay_run.id)
        .order_by(PayrollRunLine.employee_number)
    )
    lines = list(lines_result.scalars().all())
    items_result = await db.execute(
        select(PayrollLineItem)
        .where(PayrollLineItem.pay_run_id == pay_run.id)
        .order_by(PayrollLineItem.item_type, PayrollLineItem.code)
    )
    items_by_line: dict[UUID, list[PayrollLineItem]] = defaultdict(list)
    for item in items_result.scalars().all():
        items_by_line[item.pay_run_line_id].append(item)

    ledger_result = await db.execute(
        select(PayrollLedgerEntry)
        .where(PayrollLedgerEntry.pay_run_id == pay_run.id)
        .order_by(PayrollLedgerEntry.sequence_number)
    )

    return PayRunRead(
        id=pay_run.id,
        tenant_id=pay_run.tenant_id,
        pay_period_id=pay_run.pay_period_id,
        status=pay_run.status,
        employee_count=pay_run.employee_count,
        gross_earnings=pay_run.gross_earnings,
        total_deductions=pay_run.total_deductions,
        net_pay=pay_run.net_pay,
        currency=pay_run.currency,
        calculation_version=pay_run.calculation_version,
        calculated_at=pay_run.calculated_at,
        ledger_entry_hash=pay_run.ledger_entry_hash,
        created_at=pay_run.created_at,
        updated_at=pay_run.updated_at,
        pay_period=PayPeriodRead.model_validate(period),
        lines=[
            PayrollRunLineRead(
                id=line.id,
                employee_id=line.employee_id,
                contract_id=line.contract_id,
                employee_number=line.employee_number,
                employee_name=line.employee_name,
                base_salary=line.base_salary,
                additional_earnings=line.additional_earnings,
                gross_pay=line.gross_pay,
                total_deductions=line.total_deductions,
                net_pay=line.net_pay,
                currency=line.currency,
                items=[
                    PayrollLineItemRead.model_validate(item)
                    for item in items_by_line[line.id]
                ],
            )
            for line in lines
        ],
        ledger_entries=[
            PayrollLedgerEntryRead.model_validate(entry)
            for entry in ledger_result.scalars().all()
        ],
    )

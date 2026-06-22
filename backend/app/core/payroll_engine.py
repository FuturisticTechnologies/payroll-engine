"""Milestone 3 basic payroll calculation engine."""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from hashlib import sha256
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.payroll_framework import PAY_FREQUENCIES
from app.models.employee import Employee
from app.models.employment import EmploymentContract
from app.models.payroll import (
    PayPeriod,
    PayrollLedgerEntry,
    PayrollLineItem,
    PayrollRun,
    PayrollRunLine,
)
from app.schemas.payroll import PayrollAdjustmentCreate, PayRunCreate

CALCULATION_VERSION = "m3-basic-v1"
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _periods_per_year(pay_frequency: str) -> Decimal:
    for frequency in PAY_FREQUENCIES:
        if frequency["code"] == pay_frequency:
            return Decimal(str(frequency["periods_per_tax_year"]))
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Unsupported pay frequency",
    )


async def calculate_and_persist_pay_run(
    db: AsyncSession,
    tenant_id: UUID,
    payload: PayRunCreate,
    *,
    created_by_user_id: UUID | None,
) -> PayrollRun:
    period = await _get_or_create_pay_period(db, tenant_id, payload)
    existing_run = await db.execute(
        select(PayrollRun.id).where(
            PayrollRun.tenant_id == tenant_id,
            PayrollRun.pay_period_id == period.id,
        )
    )
    if existing_run.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Payroll run already exists for this pay period",
        )

    eligible_rows = await _eligible_employee_contracts(db, tenant_id, payload)
    if not eligible_rows:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active employees with matching primary contracts for this pay period",
        )

    adjustments = _adjustments_by_employee(payload.adjustments)
    _ensure_adjustments_match_eligible_employees(adjustments, eligible_rows)

    now = datetime.now(UTC)
    pay_run = PayrollRun(
        tenant_id=tenant_id,
        pay_period_id=period.id,
        status="calculated",
        employee_count=0,
        gross_earnings=Decimal("0.00"),
        total_deductions=Decimal("0.00"),
        net_pay=Decimal("0.00"),
        currency="GBP",
        calculation_version=CALCULATION_VERSION,
        calculated_at=now,
        created_by_user_id=created_by_user_id,
    )
    db.add(pay_run)
    await db.flush()

    lines: list[PayrollRunLine] = []
    line_items: list[PayrollLineItem] = []
    periods = _periods_per_year(payload.pay_frequency)

    total_gross = Decimal("0.00")
    total_deductions = Decimal("0.00")
    total_net = Decimal("0.00")
    for employee, contract in eligible_rows:
        employee_adjustments = adjustments.get(employee.id, [])
        line, items = _calculate_employee_line(
            pay_run.id,
            tenant_id,
            employee,
            contract,
            periods,
            employee_adjustments,
        )
        db.add(line)
        await db.flush()
        for item in items:
            item.pay_run_line_id = line.id
            db.add(item)
        lines.append(line)
        line_items.extend(items)
        total_gross += line.gross_pay
        total_deductions += line.total_deductions
        total_net += line.net_pay

    pay_run.employee_count = len(lines)
    pay_run.gross_earnings = _money(total_gross)
    pay_run.total_deductions = _money(total_deductions)
    pay_run.net_pay = _money(total_net)
    await db.flush()

    ledger_entry = await _append_ledger_entry(
        db,
        tenant_id,
        pay_run,
        period,
        lines,
        line_items,
        created_by_user_id=created_by_user_id,
        created_at=now,
    )
    pay_run.ledger_entry_hash = ledger_entry.entry_hash
    await db.flush()
    await db.refresh(pay_run)
    return pay_run


async def _get_or_create_pay_period(
    db: AsyncSession,
    tenant_id: UUID,
    payload: PayRunCreate,
) -> PayPeriod:
    result = await db.execute(
        select(PayPeriod).where(
            PayPeriod.tenant_id == tenant_id,
            PayPeriod.tax_year == payload.tax_year,
            PayPeriod.pay_frequency == payload.pay_frequency,
            PayPeriod.period_number == payload.period_number,
        )
    )
    period = result.scalar_one_or_none()
    if period is not None:
        if (
            period.period_start != payload.period_start
            or period.period_end != payload.period_end
            or period.payment_date != payload.payment_date
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Existing pay period has different dates",
            )
        return period

    period = PayPeriod(
        tenant_id=tenant_id,
        tax_year=payload.tax_year,
        period_number=payload.period_number,
        pay_frequency=payload.pay_frequency,
        period_start=payload.period_start,
        period_end=payload.period_end,
        payment_date=payload.payment_date,
        status="open",
    )
    db.add(period)
    await db.flush()
    return period


async def _eligible_employee_contracts(
    db: AsyncSession,
    tenant_id: UUID,
    payload: PayRunCreate,
) -> list[tuple[Employee, EmploymentContract]]:
    stmt = (
        select(Employee, EmploymentContract)
        .join(
            EmploymentContract,
            EmploymentContract.employee_id == Employee.id,
        )
        .where(
            Employee.tenant_id == tenant_id,
            Employee.employment_status == "active",
            EmploymentContract.tenant_id == tenant_id,
            EmploymentContract.is_primary.is_(True),
            EmploymentContract.pay_frequency == payload.pay_frequency,
            EmploymentContract.effective_from <= payload.period_end,
            or_(
                EmploymentContract.effective_to.is_(None),
                EmploymentContract.effective_to >= payload.period_start,
            ),
        )
        .order_by(Employee.employee_number)
    )
    if payload.employee_ids is not None:
        stmt = stmt.where(Employee.id.in_(payload.employee_ids))

    result = await db.execute(stmt)
    return list(result.all())


def _adjustments_by_employee(
    adjustments: list[PayrollAdjustmentCreate],
) -> dict[UUID, list[PayrollAdjustmentCreate]]:
    grouped: dict[UUID, list[PayrollAdjustmentCreate]] = defaultdict(list)
    for adjustment in adjustments:
        grouped[adjustment.employee_id].append(adjustment)
    return grouped


def _ensure_adjustments_match_eligible_employees(
    adjustments: dict[UUID, list[PayrollAdjustmentCreate]],
    eligible_rows: list[tuple[Employee, EmploymentContract]],
) -> None:
    eligible_employee_ids = {employee.id for employee, _contract in eligible_rows}
    unknown_employee_ids = set(adjustments) - eligible_employee_ids
    if unknown_employee_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Adjustments reference employees outside this pay run",
        )


def _calculate_employee_line(
    pay_run_id: UUID,
    tenant_id: UUID,
    employee: Employee,
    contract: EmploymentContract,
    periods_per_year: Decimal,
    adjustments: list[PayrollAdjustmentCreate],
) -> tuple[PayrollRunLine, list[PayrollLineItem]]:
    annual_salary = contract.annual_salary or Decimal("0.00")
    base_salary = _money(annual_salary / periods_per_year)
    earnings = _money(
        sum(
            (adjustment.amount for adjustment in adjustments if adjustment.item_type == "earning"),
            Decimal("0.00"),
        )
    )
    deductions = _money(
        sum(
            (
                adjustment.amount
                for adjustment in adjustments
                if adjustment.item_type == "deduction"
            ),
            Decimal("0.00"),
        )
    )
    gross = _money(base_salary + earnings)
    net = _money(gross - deductions)
    if net < Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deductions cannot exceed gross pay in the M3 basic engine",
        )

    line = PayrollRunLine(
        tenant_id=tenant_id,
        pay_run_id=pay_run_id,
        employee_id=employee.id,
        contract_id=contract.id,
        employee_number=employee.employee_number,
        employee_name=f"{employee.first_name} {employee.last_name}",
        base_salary=base_salary,
        additional_earnings=earnings,
        gross_pay=gross,
        total_deductions=deductions,
        net_pay=net,
        currency=contract.currency,
    )
    items = [
        PayrollLineItem(
            tenant_id=tenant_id,
            pay_run_id=pay_run_id,
            pay_run_line_id=pay_run_id,
            employee_id=employee.id,
            item_type="earning",
            code="BASIC",
            description="Base salary",
            amount=base_salary,
            taxable=True,
            pensionable=True,
            source="contract",
        )
    ]
    for adjustment in adjustments:
        items.append(
            PayrollLineItem(
                tenant_id=tenant_id,
                pay_run_id=pay_run_id,
                pay_run_line_id=pay_run_id,
                employee_id=employee.id,
                item_type=adjustment.item_type,
                code=adjustment.code,
                description=adjustment.description,
                amount=_money(adjustment.amount),
                taxable=adjustment.taxable,
                pensionable=adjustment.pensionable,
                source="manual",
            )
        )
    return line, items


async def _append_ledger_entry(
    db: AsyncSession,
    tenant_id: UUID,
    pay_run: PayrollRun,
    period: PayPeriod,
    lines: list[PayrollRunLine],
    line_items: list[PayrollLineItem],
    *,
    created_by_user_id: UUID | None,
    created_at: datetime,
) -> PayrollLedgerEntry:
    await _lock_tenant_ledger(db, tenant_id)
    previous = await db.execute(
        select(PayrollLedgerEntry)
        .where(PayrollLedgerEntry.tenant_id == tenant_id)
        .order_by(desc(PayrollLedgerEntry.sequence_number))
        .limit(1)
        .with_for_update()
    )
    previous_entry = previous.scalar_one_or_none()
    sequence_number = 1 if previous_entry is None else previous_entry.sequence_number + 1
    previous_hash = None if previous_entry is None else previous_entry.entry_hash

    payload = _ledger_payload(pay_run, period, lines, line_items)
    payload_hash = _hash_json(payload)
    entry_hash = sha256(
        f"{previous_hash or ''}:{payload_hash}:{sequence_number}:pay_run_calculated".encode()
    ).hexdigest()
    entry = PayrollLedgerEntry(
        tenant_id=tenant_id,
        pay_run_id=pay_run.id,
        sequence_number=sequence_number,
        entry_type="pay_run_calculated",
        payload_hash=payload_hash,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
        payload=payload,
        created_by_user_id=created_by_user_id,
        created_at=created_at,
    )
    db.add(entry)
    await db.flush()
    return entry


async def _lock_tenant_ledger(db: AsyncSession, tenant_id: UUID) -> None:
    """Serialize tenant ledger appends before deriving the next chain sequence."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return

    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_key)"),
        {"lock_key": _tenant_ledger_lock_key(tenant_id)},
    )


def _tenant_ledger_lock_key(tenant_id: UUID) -> int:
    high = tenant_id.int >> 64
    low = tenant_id.int & ((1 << 64) - 1)
    lock_key = (high ^ low) & ((1 << 64) - 1)
    if lock_key >= (1 << 63):
        lock_key -= 1 << 64
    return lock_key


def _ledger_payload(
    pay_run: PayrollRun,
    period: PayPeriod,
    lines: list[PayrollRunLine],
    line_items: list[PayrollLineItem],
) -> dict[str, object]:
    items_by_employee: dict[UUID, list[PayrollLineItem]] = defaultdict(list)
    for item in line_items:
        items_by_employee[item.employee_id].append(item)

    return {
        "calculation_version": pay_run.calculation_version,
        "pay_run_id": str(pay_run.id),
        "pay_period": {
            "id": str(period.id),
            "tax_year": period.tax_year,
            "period_number": period.period_number,
            "pay_frequency": period.pay_frequency,
            "period_start": period.period_start.isoformat(),
            "period_end": period.period_end.isoformat(),
            "payment_date": period.payment_date.isoformat(),
        },
        "totals": {
            "employee_count": pay_run.employee_count,
            "gross_earnings": str(pay_run.gross_earnings),
            "total_deductions": str(pay_run.total_deductions),
            "net_pay": str(pay_run.net_pay),
            "currency": pay_run.currency,
        },
        "lines": [
            {
                "employee_id": str(line.employee_id),
                "employee_number": line.employee_number,
                "employee_name": line.employee_name,
                "contract_id": str(line.contract_id),
                "base_salary": str(line.base_salary),
                "additional_earnings": str(line.additional_earnings),
                "gross_pay": str(line.gross_pay),
                "total_deductions": str(line.total_deductions),
                "net_pay": str(line.net_pay),
                "items": [
                    {
                        "item_type": item.item_type,
                        "code": item.code,
                        "description": item.description,
                        "amount": str(item.amount),
                        "taxable": item.taxable,
                        "pensionable": item.pensionable,
                        "source": item.source,
                    }
                    for item in items_by_employee[line.employee_id]
                ],
            }
            for line in lines
        ],
    }


def _hash_json(value: dict[str, object]) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return sha256(canonical.encode()).hexdigest()

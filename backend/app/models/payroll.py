"""Milestone 3 payroll period, run and immutable ledger models."""
from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class PayPeriod(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "pay_periods"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "tax_year",
            "pay_frequency",
            "period_number",
            name="uq_pay_periods_tenant_cycle",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pay_frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")


class PayrollRun(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "pay_runs"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "pay_period_id",
            name="uq_pay_runs_tenant_pay_period",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pay_period_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pay_periods.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="calculated")
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gross_earnings: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    calculation_version: Mapped[str] = mapped_column(
        String(40), nullable=False, default="m3-basic-v1"
    )
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    ledger_entry_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)


class PayrollRunLine(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "payroll_run_lines"
    __table_args__ = (
        UniqueConstraint(
            "pay_run_id",
            "employee_id",
            name="uq_payroll_run_lines_run_employee",
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pay_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pay_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employment_contracts.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    employee_number: Mapped[str] = mapped_column(String(40), nullable=False)
    employee_name: Mapped[str] = mapped_column(String(220), nullable=False)
    base_salary: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    additional_earnings: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    gross_pay: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    total_deductions: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    net_pay: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=Decimal("0.00")
    )
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")


class PayrollLineItem(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "payroll_line_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pay_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pay_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pay_run_line_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("payroll_run_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    taxable: Mapped[bool] = mapped_column(nullable=False, default=True)
    pensionable: Mapped[bool] = mapped_column(nullable=False, default=True)
    source: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")


class PayrollLedgerEntry(UUIDPkMixin, Base):
    __tablename__ = "payroll_ledger_entries"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "sequence_number",
            name="uq_payroll_ledger_entries_tenant_sequence",
        ),
        UniqueConstraint("entry_hash", name="uq_payroll_ledger_entries_hash"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pay_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pay_runs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)
    entry_type: Mapped[str] = mapped_column(String(60), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    previous_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

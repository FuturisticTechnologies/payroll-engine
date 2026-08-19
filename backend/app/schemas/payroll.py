"""Payroll engine request and response schemas for Milestone 3."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.payroll_framework import PAY_FREQUENCIES, PAY_FREQUENCY_CODES

PayrollItemType = Literal["earning", "deduction"]


class PayrollAdjustmentCreate(BaseModel):
    employee_id: UUID
    item_type: PayrollItemType
    code: str = Field(min_length=1, max_length=40)
    description: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    taxable: bool = True
    pensionable: bool = True

    @field_validator("code", mode="before")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        if not isinstance(value, str):
            raise TypeError("Code must be a string")
        return value.strip().upper()


class PayRunCreate(BaseModel):
    tenant_id: UUID | None = None
    tax_year: int = Field(ge=2000, le=2100)
    period_number: int = Field(ge=1, le=53)
    pay_frequency: str = "monthly"
    period_start: date
    period_end: date
    payment_date: date
    employee_ids: list[UUID] | None = None
    adjustments: list[PayrollAdjustmentCreate] = Field(default_factory=list)

    @field_validator("pay_frequency")
    @classmethod
    def _valid_pay_frequency(cls, value: str) -> str:
        if value not in PAY_FREQUENCY_CODES:
            raise ValueError("Unsupported pay frequency")
        return value

    @model_validator(mode="after")
    def _dates_and_selection_are_valid(self) -> PayRunCreate:
        if self.period_end < self.period_start:
            raise ValueError("period_end cannot be before period_start")
        if self.employee_ids == []:
            raise ValueError("employee_ids must be omitted or contain at least one employee")
        periods_per_tax_year = next(
            item["periods_per_tax_year"]
            for item in PAY_FREQUENCIES
            if item["code"] == self.pay_frequency
        )
        if self.period_number > periods_per_tax_year:
            raise ValueError(
                f"period_number cannot exceed {periods_per_tax_year} for "
                f"{self.pay_frequency} pay runs"
            )
        return self


class PayPeriodRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    tax_year: int
    period_number: int
    pay_frequency: str
    period_start: date
    period_end: date
    payment_date: date
    status: str
    created_at: datetime
    updated_at: datetime


class PayrollLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    item_type: str
    code: str
    description: str
    amount: Decimal
    taxable: bool
    pensionable: bool
    source: str


class PayrollRunLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    employee_id: UUID
    contract_id: UUID
    employee_number: str
    employee_name: str
    base_salary: Decimal
    additional_earnings: Decimal
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    currency: str
    items: list[PayrollLineItemRead] = Field(default_factory=list)


class PayrollLedgerEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    pay_run_id: UUID
    sequence_number: int
    entry_type: str
    payload_hash: str
    previous_hash: str | None
    entry_hash: str
    created_at: datetime


class PayRunSummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    pay_period_id: UUID
    status: str
    employee_count: int
    gross_earnings: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    currency: str
    calculation_version: str
    calculated_at: datetime
    ledger_entry_hash: str | None
    created_at: datetime
    updated_at: datetime


class PayRunRead(PayRunSummaryRead):
    pay_period: PayPeriodRead
    lines: list[PayrollRunLineRead]
    ledger_entries: list[PayrollLedgerEntryRead]

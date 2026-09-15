"""Employment contract schemas."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.payroll_framework import CONTRACT_TYPE_CODES, PAY_FREQUENCY_CODES


class EmploymentContractCreate(BaseModel):
    tenant_id: UUID | None = None
    employee_id: UUID
    contract_type: str = "permanent"
    pay_frequency: str = "monthly"
    annual_salary: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    weekly_hours: Decimal | None = Field(default=None, ge=0, le=168, max_digits=5, decimal_places=2)
    effective_from: date
    effective_to: date | None = None
    currency: str = Field(default="GBP", min_length=3, max_length=3)
    is_primary: bool = True

    @field_validator("contract_type")
    @classmethod
    def _valid_contract_type(cls, v: str) -> str:
        if v not in CONTRACT_TYPE_CODES:
            raise ValueError("Unsupported contract type")
        return v

    @field_validator("pay_frequency")
    @classmethod
    def _valid_pay_frequency(cls, v: str) -> str:
        if v not in PAY_FREQUENCY_CODES:
            raise ValueError("Unsupported pay frequency")
        return v

    @field_validator("currency", mode="before")
    @classmethod
    def _normalize_currency(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Currency must be a string")
        return v.strip().upper()

    @model_validator(mode="after")
    def _date_range_is_valid(self) -> EmploymentContractCreate:
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to cannot be before effective_from")
        return self


class EmploymentContractRead(EmploymentContractCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime

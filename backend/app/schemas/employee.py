"""Employee request/response schemas."""
from __future__ import annotations

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

# Format: 2 letters, 6 digits, 1 letter — e.g. AB123456C.
# Real HMRC rules exclude certain prefixes; enforced at service layer later.
_NI_RE = re.compile(r"^[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$")

# Simplified UK tax code pattern covering common PAYE codes:
# 1257L, 1257M/N/T, BR, D0, D1, NT, 0T, 1257X, and K-prefix codes.
_TAX_CODE_RE = re.compile(
    r"^(BR|D0|D1|NT|0T|K[0-9]{1,4}|[0-9]{1,4}([LMNT]|X)?)$",
    re.IGNORECASE,
)


class EmployeeBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    national_insurance_number: str = Field(min_length=9, max_length=9)
    tax_code: str = Field(default="1257L", min_length=2, max_length=10)
    employment_start_date: date
    job_title: str | None = Field(default=None, max_length=150)

    @field_validator("national_insurance_number", mode="before")
    @classmethod
    def _normalize_ni(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("NI number must be a string")
        cleaned = v.replace(" ", "").upper()
        if not _NI_RE.fullmatch(cleaned):
            raise ValueError("Invalid UK National Insurance number")
        return cleaned

    @field_validator("tax_code", mode="before")
    @classmethod
    def _normalize_tax_code(cls, v: str) -> str:
        if not isinstance(v, str):
            raise TypeError("Tax code must be a string")
        cleaned = v.strip().upper()
        if not _TAX_CODE_RE.fullmatch(cleaned):
            raise ValueError("Invalid UK tax code")
        return cleaned


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

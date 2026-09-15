"""Tenant request/response schemas."""
from __future__ import annotations

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.payroll_framework import PAY_FREQUENCY_CODES

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    legal_name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=3, max_length=80)
    company_registration_number: str | None = Field(default=None, max_length=32)
    paye_reference: str | None = Field(default=None, max_length=32)
    accounts_office_reference: str | None = Field(default=None, max_length=32)
    default_pay_frequency: str = "monthly"
    status: str = Field(default="active", max_length=20)

    @field_validator("slug", mode="before")
    @classmethod
    def _normalize_slug(cls, v: str) -> str:
        if not isinstance(v, str):
            raise ValueError("Slug must be a string")
        cleaned = v.strip().lower()
        if not _SLUG_RE.fullmatch(cleaned):
            raise ValueError("Slug must contain lowercase letters, numbers and hyphens")
        return cleaned

    @field_validator("default_pay_frequency")
    @classmethod
    def _valid_pay_frequency(cls, v: str) -> str:
        if v not in PAY_FREQUENCY_CODES:
            raise ValueError("Unsupported pay frequency")
        return v


class TenantCreate(TenantBase):
    pass


class TenantRead(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

"""Payroll framework catalog schemas."""
from __future__ import annotations

from pydantic import BaseModel


class PayFrequency(BaseModel):
    code: str
    label: str
    periods_per_tax_year: int
    hmrc_payment_frequency: str


class CatalogItem(BaseModel):
    code: str
    label: str


class RoleCatalogItem(BaseModel):
    code: str
    name: str
    description: str


class PermissionCatalogItem(BaseModel):
    code: str
    description: str


class PayrollFrameworkRead(BaseModel):
    pay_frequencies: list[PayFrequency]
    contract_types: list[CatalogItem]
    ni_categories: list[CatalogItem]
    roles: list[RoleCatalogItem]
    permissions: list[PermissionCatalogItem]

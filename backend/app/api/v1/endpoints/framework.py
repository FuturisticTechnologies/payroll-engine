"""Payroll framework catalog endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.payroll_framework import (
    CONTRACT_TYPES,
    NI_CATEGORIES,
    PAY_FREQUENCIES,
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLES,
)
from app.core.rbac import AccessContext, require_permission
from app.schemas.framework import PayrollFrameworkRead

router = APIRouter()


@router.get("", response_model=PayrollFrameworkRead)
async def framework_catalog(
    access: AccessContext = Depends(require_permission("employees:read")),
) -> PayrollFrameworkRead:
    _ = access
    return PayrollFrameworkRead(
        pay_frequencies=PAY_FREQUENCIES,
        contract_types=CONTRACT_TYPES,
        ni_categories=NI_CATEGORIES,
        roles=SYSTEM_ROLES,
        permissions=SYSTEM_PERMISSIONS,
    )

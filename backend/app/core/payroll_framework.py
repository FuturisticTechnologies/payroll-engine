"""Milestone 2 payroll framework reference data."""
from __future__ import annotations

from uuid import UUID

DEFAULT_TENANT_ID = UUID("00000000-0000-4000-8000-000000000001")
DEFAULT_TENANT = {
    "id": DEFAULT_TENANT_ID,
    "name": "Snovasys Futuristic Technologies",
    "legal_name": "Snovasys Software Solutions Ltd",
    "slug": "snovasys-futuristic",
    "company_registration_number": None,
    "paye_reference": "120/AB45678",
    "accounts_office_reference": "123PA00045678",
    "default_pay_frequency": "monthly",
    "status": "active",
}

PAY_FREQUENCIES = [
    {
        "code": "weekly",
        "label": "Weekly",
        "periods_per_tax_year": 52,
        "hmrc_payment_frequency": "W1",
    },
    {
        "code": "fortnightly",
        "label": "Fortnightly",
        "periods_per_tax_year": 26,
        "hmrc_payment_frequency": "W2",
    },
    {
        "code": "four_weekly",
        "label": "Four weekly",
        "periods_per_tax_year": 13,
        "hmrc_payment_frequency": "W4",
    },
    {
        "code": "monthly",
        "label": "Monthly",
        "periods_per_tax_year": 12,
        "hmrc_payment_frequency": "M1",
    },
]

CONTRACT_TYPES = [
    {"code": "permanent", "label": "Permanent"},
    {"code": "fixed_term", "label": "Fixed term"},
    {"code": "apprentice", "label": "Apprentice"},
    {"code": "casual", "label": "Casual"},
]

NI_CATEGORIES = [
    {"code": "A", "label": "Standard employee"},
    {"code": "B", "label": "Married women and widows reduced rate"},
    {"code": "C", "label": "Employees over State Pension age"},
    {"code": "H", "label": "Apprentice under 25"},
    {"code": "J", "label": "Employee can defer National Insurance"},
    {"code": "M", "label": "Employee under 21"},
    {"code": "V", "label": "Veteran in first civilian job"},
    {"code": "Z", "label": "Employee under 21 can defer National Insurance"},
]

SYSTEM_ROLES = [
    {
        "code": "tenant_owner",
        "name": "Tenant owner",
        "description": "Full access to employer setup and payroll operations.",
    },
    {
        "code": "payroll_admin",
        "name": "Payroll admin",
        "description": "Manage employees, contracts and payroll runs.",
    },
    {
        "code": "payroll_viewer",
        "name": "Payroll viewer",
        "description": "Read-only payroll and employee access.",
    },
    {
        "code": "employee_self_service",
        "name": "Employee self service",
        "description": "Restricted employee self-service access.",
    },
]

SYSTEM_PERMISSIONS = [
    {
        "code": "tenants:manage",
        "description": "Create and maintain employer tenants.",
    },
    {
        "code": "rbac:manage",
        "description": "Assign users to tenant roles.",
    },
    {
        "code": "employees:read",
        "description": "Read employee records.",
    },
    {
        "code": "employees:write",
        "description": "Create and update employee records.",
    },
    {
        "code": "contracts:manage",
        "description": "Maintain employment contracts and pay frequencies.",
    },
    {
        "code": "payroll:read",
        "description": "Read payroll periods, runs and ledger evidence.",
    },
    {
        "code": "payroll:run",
        "description": "Execute payroll calculations and pay runs.",
    },
]

ROLE_PERMISSION_CODES = {
    "tenant_owner": [
        "tenants:manage",
        "rbac:manage",
        "employees:read",
        "employees:write",
        "contracts:manage",
        "payroll:read",
        "payroll:run",
    ],
    "payroll_admin": [
        "employees:read",
        "employees:write",
        "contracts:manage",
        "payroll:read",
        "payroll:run",
    ],
    "payroll_viewer": ["employees:read", "payroll:read"],
    "employee_self_service": ["employees:read"],
}

PAY_FREQUENCY_CODES = {item["code"] for item in PAY_FREQUENCIES}
CONTRACT_TYPE_CODES = {item["code"] for item in CONTRACT_TYPES}
NI_CATEGORY_CODES = {item["code"] for item in NI_CATEGORIES}

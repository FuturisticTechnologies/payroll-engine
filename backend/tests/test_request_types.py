"""A value of the wrong JSON type is the caller's mistake, not the server's."""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


def _employee(**overrides: object) -> dict[str, object]:
    return {
        "first_name": "Wrong",
        "last_name": "Type",
        "email": f"types-{uuid4().hex[:10]}@example.com",
        "national_insurance_number": "AB123456C",
        "tax_code": "1257L",
        "employment_start_date": "2026-04-06",
    } | overrides


def _pay_run_with_adjustment_code(code: object) -> dict[str, object]:
    employee_id = str(uuid4())
    return {
        "tax_year": 2026,
        "period_number": 1,
        "pay_frequency": "monthly",
        "period_start": "2026-04-06",
        "period_end": "2026-05-05",
        "payment_date": "2026-05-05",
        "employee_ids": [employee_id],
        "adjustments": [
            {
                "employee_id": employee_id,
                "item_type": "earning",
                "code": code,
                "description": "Bonus",
                "amount": "100.00",
            }
        ],
    }


NON_STRING_VALUES = [
    pytest.param(
        "/api/v1/employees",
        _employee(national_insurance_number=123456789),
        id="employee-ni-number",
    ),
    pytest.param("/api/v1/employees", _employee(tax_code=1257), id="employee-tax-code"),
    pytest.param("/api/v1/employees", _employee(ni_category=1), id="employee-ni-category"),
    pytest.param(
        "/api/v1/employment-contracts",
        {"employee_id": str(uuid4()), "effective_from": "2026-04-06", "currency": 826},
        id="contract-currency",
    ),
    pytest.param(
        "/api/v1/tenants",
        {"name": "Numbers Ltd", "legal_name": "Numbers Ltd", "slug": 12345},
        id="tenant-slug",
    ),
    pytest.param(
        "/api/v1/pay-runs",
        _pay_run_with_adjustment_code(42),
        id="pay-run-adjustment-code",
    ),
]


@pytest.mark.parametrize(("path", "payload"), NON_STRING_VALUES)
def test_a_number_where_text_is_expected_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    path: str,
    payload: dict[str, object],
) -> None:
    response = client.post(path, json=payload, headers=auth_headers)
    assert response.status_code == 422, response.text
    assert "must be a string" in response.text

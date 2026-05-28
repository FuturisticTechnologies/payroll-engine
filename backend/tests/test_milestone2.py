"""Milestone 2 API coverage."""
from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _tenant_payload() -> dict[str, object]:
    token = uuid4().hex[:8]
    return {
        "name": f"Client {token}",
        "legal_name": f"Client {token} Ltd",
        "slug": f"client-{token}",
        "default_pay_frequency": "monthly",
        "status": "active",
    }


def _employee_payload() -> dict[str, object]:
    unique_number = uuid4().int % 1_000_000
    token = uuid4().hex[:10]
    return {
        "first_name": "Milestone",
        "last_name": "Two",
        "email": f"m2-{token}@example.com",
        "national_insurance_number": f"AB{unique_number:06d}C",
        "tax_code": "1257L",
        "employment_start_date": "2026-05-01",
        "job_title": "Payroll Specialist",
    }


def test_default_tenant_is_seeded(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/tenants", headers=auth_headers)
    assert response.status_code == 200
    tenants = response.json()
    assert any(t["slug"] == "snovasys-futuristic" for t in tenants)


def test_framework_catalog_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/framework")
    assert response.status_code == 401


def test_framework_catalog_exposes_m2_reference_data(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get("/api/v1/framework", headers=auth_headers)
    assert response.status_code == 200
    body = response.json()
    assert {item["code"] for item in body["pay_frequencies"]} >= {"weekly", "monthly"}
    assert {item["code"] for item in body["contract_types"]} >= {"permanent", "fixed_term"}
    assert {item["code"] for item in body["roles"]} >= {"tenant_owner", "payroll_admin"}


def test_create_tenant_is_idempotent(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    payload = _tenant_payload()
    key = f"tenant-{uuid4()}"

    first = client.post(
        "/api/v1/tenants",
        json=payload,
        headers=auth_headers | {"Idempotency-Key": key},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/tenants",
        json=payload,
        headers=auth_headers | {"Idempotency-Key": key},
    )
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]

    changed = payload | {"name": "Different legal entity"}
    conflict = client.post(
        "/api/v1/tenants",
        json=changed,
        headers=auth_headers | {"Idempotency-Key": key},
    )
    assert conflict.status_code == 409


def test_employment_contract_can_be_created_for_employee(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = client.post(
        "/api/v1/employees",
        json=_employee_payload(),
        headers=auth_headers,
    )
    assert employee.status_code == 201
    employee_body = employee.json()

    contract = client.post(
        "/api/v1/employment-contracts",
        json={
            "employee_id": employee_body["id"],
            "pay_frequency": "monthly",
            "contract_type": "permanent",
            "annual_salary": "42000.00",
            "weekly_hours": "37.50",
            "effective_from": "2026-05-01",
        },
        headers=auth_headers | {"Idempotency-Key": f"contract-{uuid4()}"},
    )
    assert contract.status_code == 201
    body = contract.json()
    assert body["employee_id"] == employee_body["id"]
    assert body["tenant_id"] == employee_body["tenant_id"]
    assert body["pay_frequency"] == "monthly"


def test_employment_contract_rejects_overlap_and_second_primary(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = client.post(
        "/api/v1/employees",
        json=_employee_payload(),
        headers=auth_headers,
    )
    assert employee.status_code == 201
    employee_id = employee.json()["id"]
    first = client.post(
        "/api/v1/employment-contracts",
        json={
            "employee_id": employee_id,
            "pay_frequency": "monthly",
            "contract_type": "permanent",
            "annual_salary": "42000.00",
            "weekly_hours": "37.50",
            "effective_from": "2026-05-01",
            "effective_to": "2026-12-31",
        },
        headers=auth_headers,
    )
    assert first.status_code == 201

    overlap = client.post(
        "/api/v1/employment-contracts",
        json={
            "employee_id": employee_id,
            "pay_frequency": "monthly",
            "contract_type": "permanent",
            "annual_salary": "43000.00",
            "weekly_hours": "37.50",
            "effective_from": "2026-06-01",
            "effective_to": "2027-01-31",
            "is_primary": False,
        },
        headers=auth_headers,
    )
    assert overlap.status_code == 409

    second_primary = client.post(
        "/api/v1/employment-contracts",
        json={
            "employee_id": employee_id,
            "pay_frequency": "monthly",
            "contract_type": "permanent",
            "annual_salary": "44000.00",
            "weekly_hours": "37.50",
            "effective_from": "2027-01-01",
        },
        headers=auth_headers,
    )
    assert second_primary.status_code == 409

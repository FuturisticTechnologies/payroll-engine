"""Milestone 3 payroll engine coverage."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient


def _employee_payload() -> dict[str, object]:
    unique_number = uuid4().int % 1_000_000
    token = uuid4().hex[:10]
    return {
        "first_name": "Milestone",
        "last_name": "Three",
        "email": f"m3-{token}@example.com",
        "national_insurance_number": f"AB{unique_number:06d}C",
        "tax_code": "1257L",
        "employment_start_date": "2026-06-01",
        "job_title": "Payroll Engine Tester",
    }


def _pay_run_payload(employee_id: str, tax_year: int) -> dict[str, object]:
    return {
        "tax_year": tax_year,
        "period_number": 6,
        "pay_frequency": "monthly",
        "period_start": f"{tax_year}-06-01",
        "period_end": f"{tax_year}-06-30",
        "payment_date": f"{tax_year}-06-30",
        "employee_ids": [employee_id],
        "adjustments": [
            {
                "employee_id": employee_id,
                "item_type": "earning",
                "code": "bonus",
                "description": "Monthly bonus",
                "amount": "250.00",
            },
            {
                "employee_id": employee_id,
                "item_type": "deduction",
                "code": "advance",
                "description": "Salary advance repayment",
                "amount": "100.00",
                "taxable": False,
                "pensionable": False,
            },
        ],
    }


def _create_employee_with_contract(
    client: TestClient,
    auth_headers: dict[str, str],
) -> dict[str, object]:
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
            "annual_salary": "62400.00",
            "weekly_hours": "37.50",
            "effective_from": "2026-01-01",
        },
        headers=auth_headers | {"Idempotency-Key": f"m3-contract-{uuid4()}"},
    )
    assert contract.status_code == 201
    return employee_body


def test_milestone_reports_m3(client: TestClient) -> None:
    response = client.get("/api/v1/meta/milestone")
    assert response.status_code == 200
    body = response.json()
    assert body["milestone"] == "3"
    assert body["status"] == "complete"


def test_pay_runs_require_authentication(client: TestClient) -> None:
    response = client.get("/api/v1/pay-runs")
    assert response.status_code == 401


def test_pay_run_calculates_earnings_deductions_and_ledger(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = _create_employee_with_contract(client, auth_headers)
    tax_year = 2060 + (uuid4().int % 30)
    payload = _pay_run_payload(employee["id"], tax_year)
    key = f"pay-run-{uuid4()}"

    first = client.post(
        "/api/v1/pay-runs",
        json=payload,
        headers=auth_headers | {"Idempotency-Key": key},
    )
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "calculated"
    assert body["employee_count"] == 1
    assert Decimal(str(body["gross_earnings"])) == Decimal("5450.00")
    assert Decimal(str(body["total_deductions"])) == Decimal("100.00")
    assert Decimal(str(body["net_pay"])) == Decimal("5350.00")
    assert body["ledger_entry_hash"]
    assert len(body["ledger_entries"]) == 1
    assert body["ledger_entries"][0]["entry_hash"] == body["ledger_entry_hash"]

    line = body["lines"][0]
    assert line["employee_id"] == employee["id"]
    assert Decimal(str(line["base_salary"])) == Decimal("5200.00")
    assert Decimal(str(line["additional_earnings"])) == Decimal("250.00")
    assert {item["code"] for item in line["items"]} == {"BASIC", "BONUS", "ADVANCE"}

    replay = client.post(
        "/api/v1/pay-runs",
        json=payload,
        headers=auth_headers | {"Idempotency-Key": key},
    )
    assert replay.status_code == 201
    assert replay.json()["id"] == body["id"]

    fetched = client.get(f"/api/v1/pay-runs/{body['id']}", headers=auth_headers)
    assert fetched.status_code == 200
    assert fetched.json()["ledger_entry_hash"] == body["ledger_entry_hash"]

    ledger = client.get(f"/api/v1/pay-runs/{body['id']}/ledger", headers=auth_headers)
    assert ledger.status_code == 200
    assert ledger.json()[0]["payload_hash"] == body["ledger_entries"][0]["payload_hash"]


def test_pay_run_rejects_duplicate_period_without_idempotency(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = _create_employee_with_contract(client, auth_headers)
    tax_year = 2090 + (uuid4().int % 10)
    payload = _pay_run_payload(employee["id"], tax_year)

    first = client.post("/api/v1/pay-runs", json=payload, headers=auth_headers)
    assert first.status_code == 201

    duplicate = client.post("/api/v1/pay-runs", json=payload, headers=auth_headers)
    assert duplicate.status_code == 409


def test_pay_run_ledger_links_successive_runs_for_tenant(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = _create_employee_with_contract(client, auth_headers)
    # Pay periods are unique per tenant, and the tests above draw their years
    # from 2060-2099, so this one keeps to 2040-2059.
    first_year = 2040 + 2 * (uuid4().int % 10)

    first = client.post(
        "/api/v1/pay-runs",
        json=_pay_run_payload(employee["id"], first_year),
        headers=auth_headers,
    )
    assert first.status_code == 201
    first_body = first.json()

    second = client.post(
        "/api/v1/pay-runs",
        json=_pay_run_payload(employee["id"], first_year + 1),
        headers=auth_headers,
    )
    assert second.status_code == 201
    second_body = second.json()

    assert first_body["ledger_entries"][0]["sequence_number"] + 1 == second_body[
        "ledger_entries"
    ][0]["sequence_number"]
    assert second_body["ledger_entries"][0]["previous_hash"] == first_body[
        "ledger_entry_hash"
    ]


def test_pay_run_rejects_invalid_period_for_frequency(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    employee = _create_employee_with_contract(client, auth_headers)
    payload = _pay_run_payload(employee["id"], 2088) | {
        "period_number": 13,
        "pay_frequency": "monthly",
    }

    response = client.post("/api/v1/pay-runs", json=payload, headers=auth_headers)
    assert response.status_code == 422
    assert "period_number cannot exceed 12" in response.text

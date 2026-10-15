"""Regression pack: input validation on the pay-run API.

Every request here is refused before it can reach the payroll engine, so none
of these cases create a pay period or touch the ledger. The one exception is
the tax-year regression at the bottom, which needs a real run to collide with.
"""
from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

PAY_RUNS = "/api/v1/pay-runs"


def _pay_run(**overrides: object) -> dict[str, object]:
    return {
        "tax_year": 2026,
        "period_number": 3,
        "pay_frequency": "monthly",
        "period_start": "2026-06-01",
        "period_end": "2026-06-30",
        "payment_date": "2026-06-30",
    } | overrides


def _adjustment(**overrides: object) -> dict[str, object]:
    return {
        "employee_id": str(uuid4()),
        "item_type": "earning",
        "code": "BONUS",
        "description": "Bonus",
        "amount": "100.00",
    } | overrides


def _error_fields(response_json: dict[str, object]) -> set[str]:
    """The last path segment of each field FastAPI reports as invalid."""
    detail = response_json["detail"]
    assert isinstance(detail, list)
    return {str(error["loc"][-1]) for error in detail}


# --- boundary values --------------------------------------------------------

BOUNDARY_VIOLATIONS = [
    pytest.param({"tax_year": 1999}, id="tax-year-below-2000"),
    pytest.param({"tax_year": 2101}, id="tax-year-above-2100"),
    pytest.param({"period_number": 0}, id="period-zero"),
    pytest.param({"period_number": 54}, id="period-above-53"),
    pytest.param({"period_number": 13}, id="period-13-monthly"),
    pytest.param({"pay_frequency": "weekly", "period_number": 53}, id="period-53-weekly"),
    pytest.param({"pay_frequency": "daily"}, id="unknown-frequency"),
    pytest.param({"pay_frequency": "Monthly"}, id="frequency-is-case-sensitive"),
    pytest.param({"adjustments": [_adjustment(amount="0")]}, id="adjustment-zero"),
    pytest.param({"adjustments": [_adjustment(amount="-5.00")]}, id="adjustment-negative"),
    pytest.param({"adjustments": [_adjustment(amount="10.005")]}, id="adjustment-sub-penny"),
    pytest.param(
        {"adjustments": [_adjustment(amount="1000000000000.00")]},
        id="adjustment-too-many-digits",
    ),
    pytest.param({"adjustments": [_adjustment(item_type="bonus")]}, id="adjustment-bad-type"),
    pytest.param({"adjustments": [_adjustment(code="")]}, id="adjustment-empty-code"),
    pytest.param({"adjustments": [_adjustment(code="   ")]}, id="adjustment-blank-code"),
    pytest.param({"adjustments": [_adjustment(code="X" * 41)]}, id="adjustment-long-code"),
    pytest.param({"adjustments": [_adjustment(description="")]}, id="adjustment-no-description"),
    pytest.param(
        {"adjustments": [_adjustment(description="d" * 256)]},
        id="adjustment-long-description",
    ),
    pytest.param({"employee_ids": []}, id="empty-employee-selection"),
    pytest.param({"employee_ids": ["not-a-uuid"]}, id="employee-id-not-uuid"),
    pytest.param({"tenant_id": "not-a-uuid"}, id="tenant-id-not-uuid"),
]


@pytest.mark.parametrize("overrides", BOUNDARY_VIOLATIONS)
def test_out_of_bounds_pay_run_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    overrides: dict[str, object],
) -> None:
    response = client.post(PAY_RUNS, json=_pay_run(**overrides), headers=auth_headers)
    assert response.status_code == 422, response.text


# --- invalid dates ----------------------------------------------------------

MALFORMED_DATES = ["2026-02-30", "2026-13-01", "2026-06-31", "30/06/2026", "not-a-date", ""]


@pytest.mark.parametrize("value", MALFORMED_DATES)
@pytest.mark.parametrize("field", ["period_start", "period_end", "payment_date"])
def test_malformed_date_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    field: str,
    value: str,
) -> None:
    response = client.post(PAY_RUNS, json=_pay_run(**{field: value}), headers=auth_headers)
    assert response.status_code == 422, response.text
    assert field in _error_fields(response.json())


def test_period_ending_before_it_starts_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(
        PAY_RUNS,
        json=_pay_run(period_start="2026-06-30", period_end="2026-06-01"),
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "period_end cannot be before period_start" in response.text


@pytest.mark.parametrize(
    "payment_date",
    ["2026-04-05", "2027-04-06", "2031-06-30"],
    ids=["before-tax-year", "after-tax-year", "years-later"],
)
def test_payment_date_outside_the_tax_year_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    payment_date: str,
) -> None:
    response = client.post(
        PAY_RUNS,
        json=_pay_run(period_start="2026-04-01", period_end="2026-04-01",
                      payment_date=payment_date),
        headers=auth_headers,
    )
    assert response.status_code == 422, response.text
    assert "payment_date must fall within tax year 2026-2027" in response.text


# --- missing fields ---------------------------------------------------------

REQUIRED_PAY_RUN_FIELDS = ["tax_year", "period_number", "period_start", "period_end",
                           "payment_date"]
REQUIRED_ADJUSTMENT_FIELDS = ["employee_id", "item_type", "code", "description", "amount"]


@pytest.mark.parametrize("field", REQUIRED_PAY_RUN_FIELDS)
def test_missing_pay_run_field_is_reported_by_name(
    client: TestClient,
    auth_headers: dict[str, str],
    field: str,
) -> None:
    payload = _pay_run()
    del payload[field]
    response = client.post(PAY_RUNS, json=payload, headers=auth_headers)
    assert response.status_code == 422
    assert field in _error_fields(response.json())


@pytest.mark.parametrize("field", REQUIRED_ADJUSTMENT_FIELDS)
def test_missing_adjustment_field_is_reported_by_name(
    client: TestClient,
    auth_headers: dict[str, str],
    field: str,
) -> None:
    adjustment = _adjustment()
    del adjustment[field]
    response = client.post(PAY_RUNS, json=_pay_run(adjustments=[adjustment]),
                           headers=auth_headers)
    assert response.status_code == 422
    assert field in _error_fields(response.json())


@pytest.mark.parametrize(
    "body",
    [{}, [], "pay run", None],
    ids=["empty-object", "array", "string", "null"],
)
def test_body_that_is_not_a_pay_run_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    body: object,
) -> None:
    response = client.post(PAY_RUNS, json=body, headers=auth_headers)
    assert response.status_code == 422, response.text


def test_explicit_null_for_a_required_field_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.post(PAY_RUNS, json=_pay_run(payment_date=None), headers=auth_headers)
    assert response.status_code == 422
    assert "payment_date" in _error_fields(response.json())


# --- path and query parameters ----------------------------------------------


@pytest.mark.parametrize("suffix", ["", "/ledger"])
def test_pay_run_id_that_is_not_a_uuid_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    suffix: str,
) -> None:
    response = client.get(f"{PAY_RUNS}/not-a-uuid{suffix}", headers=auth_headers)
    assert response.status_code == 422


@pytest.mark.parametrize("suffix", ["", "/ledger"])
def test_unknown_pay_run_is_not_found(
    client: TestClient,
    auth_headers: dict[str, str],
    suffix: str,
) -> None:
    response = client.get(f"{PAY_RUNS}/{uuid4()}{suffix}", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.parametrize(
    "query",
    ["limit=abc", "offset=abc", "limit=1.5", "limit=", "offset=1000001", "tenant_id=nope"],
)
def test_malformed_list_query_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    query: str,
) -> None:
    response = client.get(f"{PAY_RUNS}?{query}", headers=auth_headers)
    assert response.status_code == 422, response.text


def test_page_size_is_honoured_at_its_smallest(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get(f"{PAY_RUNS}?limit=1", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) <= 1


def test_offset_at_its_maximum_returns_an_empty_page(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    response = client.get(f"{PAY_RUNS}?offset=1000000", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


# --- regression: tax year must agree with the dates -------------------------


def test_same_period_cannot_be_run_again_under_another_tax_year(
    client: TestClient,
    auth_headers: dict[str, str],
) -> None:
    """Before SNOV-310 the second request was a 201: a second payroll for June.

    Pay periods are unique on (tax_year, frequency, period_number), so changing
    only ``tax_year`` used to slip past the duplicate-period guard.
    """
    employee = client.post(
        "/api/v1/employees",
        json={
            "first_name": "Tax",
            "last_name": "Year",
            "email": f"snov310-{uuid4().hex[:10]}@example.com",
            "national_insurance_number": f"AB{uuid4().int % 1_000_000:06d}C",
            "tax_code": "1257L",
            "employment_start_date": "2026-01-01",
        },
        headers=auth_headers,
    )
    assert employee.status_code == 201
    employee_id = employee.json()["id"]
    contract = client.post(
        "/api/v1/employment-contracts",
        json={
            "employee_id": employee_id,
            "pay_frequency": "monthly",
            "contract_type": "permanent",
            "annual_salary": "30000.00",
            "effective_from": "2026-01-01",
        },
        headers=auth_headers,
    )
    assert contract.status_code == 201

    # Other pay-run tests draw years from 2040-2099; this one keeps to the 2030s.
    year = 2030 + uuid4().int % 10
    dates = {
        "period_start": f"{year}-06-01",
        "period_end": f"{year}-06-30",
        "payment_date": f"{year}-06-30",
        "employee_ids": [employee_id],
    }
    first = client.post(PAY_RUNS, json=_pay_run(tax_year=year, **dates), headers=auth_headers)
    assert first.status_code == 201, first.text

    again = client.post(PAY_RUNS, json=_pay_run(tax_year=year + 1, **dates),
                        headers=auth_headers)
    assert again.status_code == 422, again.text

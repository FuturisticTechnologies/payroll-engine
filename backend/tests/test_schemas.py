"""Unit tests for Pydantic schemas (no database required)."""
from __future__ import annotations

from datetime import date

import pytest
from app.schemas.employee import EmployeeCreate
from pydantic import ValidationError


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "first_name": "Jane",
        "last_name": "Doe",
        "email": "jane.doe@example.com",
        "national_insurance_number": "AB123456C",
        "tax_code": "1257L",
        "employment_start_date": date(2026, 4, 10),
        "job_title": "Payroll Officer",
    }
    base.update(overrides)
    return base


def test_employee_create_happy_path() -> None:
    emp = EmployeeCreate(**_payload())
    assert emp.national_insurance_number == "AB123456C"
    assert emp.tax_code == "1257L"


def test_ni_number_is_uppercased_and_stripped() -> None:
    emp = EmployeeCreate(**_payload(national_insurance_number=" ab 123 456 c "))
    assert emp.national_insurance_number == "AB123456C"


def test_ni_number_invalid_format_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(**_payload(national_insurance_number="123456789"))


def test_tax_code_br_accepted() -> None:
    emp = EmployeeCreate(**_payload(tax_code="br"))
    assert emp.tax_code == "BR"


def test_tax_code_k_prefix_accepted() -> None:
    emp = EmployeeCreate(**_payload(tax_code="k497"))
    assert emp.tax_code == "K497"


def test_tax_code_suffix_k_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(**_payload(tax_code="497K"))


def test_tax_code_garbage_rejected() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(**_payload(tax_code="ZZZZZZ"))


def test_email_must_be_valid() -> None:
    with pytest.raises(ValidationError):
        EmployeeCreate(**_payload(email="not-an-email"))

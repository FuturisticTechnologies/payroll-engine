"""Boundary values accepted and rejected by ``PayRunCreate`` (no database required).

The API-level pack in ``test_pay_run_validation.py`` proves bad input is
refused over HTTP. Values *at* a bound are checked here instead, because
accepting them over HTTP would create a pay run and a pay period per case.
"""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from app.core.payroll_framework import PAY_FREQUENCIES
from app.schemas.payroll import PayrollAdjustmentCreate, PayRunCreate, uk_tax_year_bounds
from pydantic import ValidationError


def _pay_run(**overrides: object) -> dict[str, object]:
    return {
        "tax_year": 2026,
        "period_number": 3,
        "pay_frequency": "monthly",
        "period_start": date(2026, 6, 1),
        "period_end": date(2026, 6, 30),
        "payment_date": date(2026, 6, 30),
    } | overrides


def _adjustment(**overrides: object) -> dict[str, object]:
    return {
        "employee_id": uuid4(),
        "item_type": "earning",
        "code": "BONUS",
        "description": "Bonus",
        "amount": "1.00",
    } | overrides


# --- tax year ---------------------------------------------------------------


@pytest.mark.parametrize("tax_year", [2000, 2100])
def test_tax_year_bounds_are_inclusive(tax_year: int) -> None:
    start, _end = uk_tax_year_bounds(tax_year)
    run = PayRunCreate(**_pay_run(tax_year=tax_year, period_start=start, period_end=start,
                                  payment_date=start))
    assert run.tax_year == tax_year


@pytest.mark.parametrize("tax_year", [1999, 2101])
def test_tax_year_outside_bounds_is_rejected(tax_year: int) -> None:
    with pytest.raises(ValidationError, match="tax_year"):
        PayRunCreate(**_pay_run(tax_year=tax_year))


def test_uk_tax_year_runs_from_6_april_to_5_april() -> None:
    assert uk_tax_year_bounds(2026) == (date(2026, 4, 6), date(2027, 4, 5))


@pytest.mark.parametrize(
    "payment_date",
    [date(2026, 4, 6), date(2027, 4, 5)],
    ids=["first-day", "last-day"],
)
def test_payment_date_on_either_edge_of_the_tax_year_is_accepted(payment_date: date) -> None:
    run = PayRunCreate(**_pay_run(period_start=date(2026, 4, 1), period_end=date(2026, 4, 1),
                                  payment_date=payment_date))
    assert run.payment_date == payment_date


@pytest.mark.parametrize(
    "payment_date",
    [date(2026, 4, 5), date(2027, 4, 6)],
    ids=["day-before", "day-after"],
)
def test_payment_date_just_outside_the_tax_year_is_rejected(payment_date: date) -> None:
    with pytest.raises(ValidationError, match="payment_date must fall within tax year 2026"):
        PayRunCreate(**_pay_run(period_start=date(2026, 4, 1), period_end=date(2026, 4, 1),
                                payment_date=payment_date))


# --- period number and dates ---------------------------------------------


@pytest.mark.parametrize(
    ("pay_frequency", "periods"),
    [(item["code"], item["periods_per_tax_year"]) for item in PAY_FREQUENCIES],
)
def test_last_period_of_each_frequency_is_accepted_and_the_next_rejected(
    pay_frequency: str,
    periods: int,
) -> None:
    last = PayRunCreate(**_pay_run(pay_frequency=pay_frequency, period_number=periods))
    assert last.period_number == periods

    with pytest.raises(ValidationError, match=f"period_number cannot exceed {periods}"):
        PayRunCreate(**_pay_run(pay_frequency=pay_frequency, period_number=periods + 1))


@pytest.mark.parametrize("period_number", [0, -1, 54])
def test_period_number_outside_field_bounds_is_rejected(period_number: int) -> None:
    with pytest.raises(ValidationError, match="period_number"):
        PayRunCreate(**_pay_run(period_number=period_number))


def test_single_day_period_is_accepted() -> None:
    run = PayRunCreate(**_pay_run(period_start=date(2026, 6, 1), period_end=date(2026, 6, 1)))
    assert run.period_start == run.period_end


# --- adjustments ------------------------------------------------------------


@pytest.mark.parametrize("amount", ["0.01", "999999999999.99"], ids=["smallest", "largest"])
def test_adjustment_amount_at_its_bounds_is_accepted(amount: str) -> None:
    assert str(PayrollAdjustmentCreate(**_adjustment(amount=amount)).amount) == amount


@pytest.mark.parametrize(
    "amount",
    ["0", "0.00", "-0.01", "0.001", "1000000000000.00"],
    ids=["zero", "zero-pence", "negative", "sub-penny", "fifteen-digits"],
)
def test_adjustment_amount_outside_its_bounds_is_rejected(amount: str) -> None:
    with pytest.raises(ValidationError, match="amount"):
        PayrollAdjustmentCreate(**_adjustment(amount=amount))


def test_adjustment_code_is_normalised_before_length_is_checked() -> None:
    assert PayrollAdjustmentCreate(**_adjustment(code="  bonus ")).code == "BONUS"
    assert len(PayrollAdjustmentCreate(**_adjustment(code="x" * 40)).code) == 40

    with pytest.raises(ValidationError, match="code"):
        PayrollAdjustmentCreate(**_adjustment(code="   "))
    with pytest.raises(ValidationError, match="code"):
        PayrollAdjustmentCreate(**_adjustment(code="x" * 41))

"""Statutory payment rules driven by effective-dated reference data (SNOV-442).

Every rate, threshold and limit that SSP, SMP and SPP depend on is read from a
``StatutoryRate`` row - the ``statutory_payment_rates`` table in the database,
seeded from ``app/reference_data/statutory_payment_rates.csv``. Nothing in this
module knows what any of those values are. The static guard in
``tests/test_statutory_reference.py`` fails the build if one is typed in here.

Rows are selected by the date the payment relates to, never by today's date,
so a pay run recalculated for a prior period uses the values in force then.

Pure functions only: no database, no FastAPI. The async loader that reads the
table lives in ``app.core.statutory_reference``.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Any

SCHEMES = ("SSP", "SMP", "SPP")
RATE_RULES = ("flat_rate_only", "percentage_only", "lower_of_flat_and_percentage")
ROUNDING_RULES = {"round_up_penny": ROUND_CEILING, "round_half_up_penny": ROUND_HALF_UP}

PENNY = Decimal("0.01")
DAYS_PER_WEEK = 7


class StatutoryReferenceError(LookupError):
    """No usable reference data for the scheme and date asked for.

    Raised rather than falling back to another year's values: paying the
    wrong rate silently is worse than refusing to pay until the data exists.
    """


@dataclass(frozen=True)
class StatutoryRate:
    """One effective-dated row of statutory payment reference data."""

    tax_year: int
    scheme: str
    rate_period: str
    period_start_week: int
    period_end_week: int
    effective_from: date
    effective_to: date | None
    awe_percentage: Decimal | None
    weekly_flat_rate: Decimal | None
    rate_rule: str
    lower_earnings_limit_weekly: Decimal | None
    relevant_period_weeks: int
    qualifying_week_offset_weeks: int | None
    continuous_employment_weeks: int | None
    waiting_days: int
    max_entitlement_weeks: int
    payment_window_weeks: int | None
    rounding: str
    source_reference: str
    source_url: str

    def in_force_on(self, on: date) -> bool:
        return self.effective_from <= on and (self.effective_to is None or on <= self.effective_to)

    def covers_week(self, week_number: int) -> bool:
        return self.period_start_week <= week_number <= self.period_end_week

    @classmethod
    def from_mapping(cls, row: Mapping[str, Any]) -> StatutoryRate:
        """Build from a CSV row, an ORM object's ``__dict__`` or a DB mapping."""

        def _dec(key: str) -> Decimal | None:
            value = row.get(key)
            return None if value in (None, "") else Decimal(str(value))

        def _int(key: str) -> int | None:
            value = row.get(key)
            return None if value in (None, "") else int(value)

        def _date(key: str) -> date | None:
            value = row.get(key)
            if value in (None, ""):
                return None
            return value if isinstance(value, date) else date.fromisoformat(str(value))

        effective_from = _date("effective_from")
        if effective_from is None:
            raise ValueError("effective_from is required on every statutory rate row")
        return cls(
            tax_year=int(row["tax_year"]),
            scheme=str(row["scheme"]),
            rate_period=str(row["rate_period"]),
            period_start_week=int(row["period_start_week"]),
            period_end_week=int(row["period_end_week"]),
            effective_from=effective_from,
            effective_to=_date("effective_to"),
            awe_percentage=_dec("awe_percentage"),
            weekly_flat_rate=_dec("weekly_flat_rate"),
            rate_rule=str(row["rate_rule"]),
            lower_earnings_limit_weekly=_dec("lower_earnings_limit_weekly"),
            relevant_period_weeks=int(row["relevant_period_weeks"]),
            qualifying_week_offset_weeks=_int("qualifying_week_offset_weeks"),
            continuous_employment_weeks=_int("continuous_employment_weeks"),
            waiting_days=int(row["waiting_days"]),
            max_entitlement_weeks=int(row["max_entitlement_weeks"]),
            payment_window_weeks=_int("payment_window_weeks"),
            rounding=str(row["rounding"]),
            source_reference=str(row.get("source_reference") or ""),
            source_url=str(row.get("source_url") or ""),
        )


# ---------------------------------------------------------------- selection --
def rates_in_force(rows: Iterable[StatutoryRate], scheme: str, on: date) -> list[StatutoryRate]:
    """The rows for ``scheme`` in force on ``on``, ordered by rate period weeks.

    Raises ``StatutoryReferenceError`` when nothing is in force, or when two rows
    for the same rate period overlap - either would make the payment ambiguous.
    """
    if scheme not in SCHEMES:
        raise StatutoryReferenceError(f"unknown statutory scheme {scheme!r}")
    selected = sorted(
        (row for row in rows if row.scheme == scheme and row.in_force_on(on)),
        key=lambda row: row.period_start_week,
    )
    if not selected:
        raise StatutoryReferenceError(
            f"no {scheme} reference data in force on {on.isoformat()}; "
            "load the rates for that tax year before running this period"
        )
    periods = [row.rate_period for row in selected]
    if len(periods) != len(set(periods)):
        raise StatutoryReferenceError(
            f"overlapping {scheme} reference rows in force on {on.isoformat()}: {periods}"
        )
    return selected


def rate_for_week(rates: Iterable[StatutoryRate], week_number: int) -> StatutoryRate:
    """The rate period row that covers payment week ``week_number`` (1-based)."""
    for row in rates:
        if row.covers_week(week_number):
            return row
    raise StatutoryReferenceError(f"no rate period covers week {week_number}")


# ------------------------------------------------------------- calculation --
def _round(value: Decimal, rate: StatutoryRate) -> Decimal:
    try:
        mode = ROUNDING_RULES[rate.rounding]
    except KeyError as exc:
        raise StatutoryReferenceError(f"unknown rounding rule {rate.rounding!r}") from exc
    return value.quantize(PENNY, rounding=mode)


def meets_earnings_test(rate: StatutoryRate, average_weekly_earnings: Decimal) -> bool:
    """Average weekly earnings at or above the lower earnings limit.

    A row with no limit (SSP from 6 April 2026) has no earnings test.
    """
    limit = rate.lower_earnings_limit_weekly
    return limit is None or average_weekly_earnings >= limit


def weekly_rate_unrounded(rate: StatutoryRate, average_weekly_earnings: Decimal) -> Decimal:
    """Weekly amount under one rate period row, before rounding."""
    percentage_amount = (
        average_weekly_earnings * rate.awe_percentage if rate.awe_percentage is not None else None
    )
    if rate.rate_rule == "flat_rate_only":
        return _require(rate.weekly_flat_rate, rate, "weekly_flat_rate")
    if rate.rate_rule == "percentage_only":
        return _require(percentage_amount, rate, "awe_percentage")
    if rate.rate_rule == "lower_of_flat_and_percentage":
        return min(
            _require(rate.weekly_flat_rate, rate, "weekly_flat_rate"),
            _require(percentage_amount, rate, "awe_percentage"),
        )
    raise StatutoryReferenceError(f"unknown rate rule {rate.rate_rule!r}")


def weekly_rate(rate: StatutoryRate, average_weekly_earnings: Decimal) -> Decimal:
    """Weekly amount payable under one rate period row, rounded per the row."""
    return _round(weekly_rate_unrounded(rate, average_weekly_earnings), rate)


def _require(value: Decimal | None, rate: StatutoryRate, field: str) -> Decimal:
    if value is None:
        raise StatutoryReferenceError(
            f"{rate.scheme} {rate.rate_period} from {rate.effective_from} has rule "
            f"{rate.rate_rule} but no {field}"
        )
    return value


# ---------------------------------------------------------------------- SSP --
def ssp_daily_rate(
    rate: StatutoryRate, average_weekly_earnings: Decimal, qualifying_days_per_week: int
) -> Decimal:
    """Unrounded daily SSP: the weekly rate spread over the qualifying days.

    HMRC publishes daily rates unrounded; only the amount paid is rounded.
    """
    if not 1 <= qualifying_days_per_week <= DAYS_PER_WEEK:
        raise ValueError("qualifying_days_per_week must be between 1 and 7")
    weekly = weekly_rate_unrounded(rate, average_weekly_earnings)
    return weekly / Decimal(qualifying_days_per_week)


def ssp_payable_days(rate: StatutoryRate, qualifying_days_of_sickness: int) -> int:
    """Qualifying days SSP is paid for, after the row's waiting days."""
    return max(qualifying_days_of_sickness - rate.waiting_days, 0)


def ssp_amount(
    rate: StatutoryRate,
    average_weekly_earnings: Decimal,
    qualifying_days_per_week: int,
    qualifying_days_of_sickness: int,
) -> Decimal:
    """SSP due for one spell, or zero when the earnings test is not met."""
    if not meets_earnings_test(rate, average_weekly_earnings):
        return Decimal("0.00")
    days = ssp_payable_days(rate, qualifying_days_of_sickness)
    daily = ssp_daily_rate(rate, average_weekly_earnings, qualifying_days_per_week)
    return _round(daily * Decimal(days), rate)


# ---------------------------------------------------------------- SMP / SPP --
def weekly_schedule(rates: list[StatutoryRate], average_weekly_earnings: Decimal) -> list[Decimal]:
    """Amount for each payment week of the entitlement, from the rows given.

    For SMP this yields the higher-rate weeks then the standard-rate weeks;
    for SPP, the paternity weeks. The length is the row's entitlement.
    """
    if not rates:
        raise StatutoryReferenceError("no rate rows supplied")
    weeks = max(row.max_entitlement_weeks for row in rates)
    return [
        weekly_rate(rate_for_week(rates, week), average_weekly_earnings)
        for week in range(1, weeks + 1)
    ]


def qualifying_week_start(rate: StatutoryRate, expected_week_of_childbirth: date) -> date:
    """Start of the qualifying week, N weeks before the expected week of childbirth."""
    offset = rate.qualifying_week_offset_weeks
    if offset is None:
        raise StatutoryReferenceError(f"{rate.scheme} row has no qualifying week offset")
    return expected_week_of_childbirth - timedelta(weeks=offset)


def spp_window_end(rate: StatutoryRate, birth_date: date) -> date:
    """Last day paternity pay may be paid for: the row's window after the birth."""
    window = rate.payment_window_weeks
    if window is None:
        raise StatutoryReferenceError(f"{rate.scheme} row has no payment window")
    return birth_date + timedelta(weeks=window) - timedelta(days=1)


def has_continuous_employment(rate: StatutoryRate, weeks_employed: int) -> bool:
    required = rate.continuous_employment_weeks
    return required is None or weeks_employed >= required

"""Statutory payment reference data and the rules that read it (SNOV-442).

Runs without a database: the seed CSV, the migration's frozen copy of it and
the pure calculation module are all checked directly. The database round trip
is in ``test_statutory_reference_db.py``.

Expected figures are HMRC's published ones, not values recomputed from the
seed - a test that derives its expectation from the data under test cannot
catch a typo in that data.
"""
from __future__ import annotations

import ast
import csv
from datetime import date, timedelta
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

import pytest
from app.core.statutory_pay import (
    StatutoryRate,
    StatutoryReferenceError,
    has_continuous_employment,
    meets_earnings_test,
    qualifying_week_start,
    rates_in_force,
    spp_window_end,
    ssp_amount,
    ssp_daily_rate,
    ssp_payable_days,
    weekly_rate,
    weekly_schedule,
)

APP = Path(__file__).resolve().parents[1] / "app"
SEED_CSV = APP / "reference_data" / "statutory_payment_rates.csv"
MIGRATION = (
    APP / "db" / "migrations" / "versions" / "20261127_0008_m8_statutory_payment_reference_data.py"
)

#: Modules that calculate statutory pay. None may contain a rate or threshold.
CALCULATION_MODULES = [
    APP / "core" / "statutory_pay.py",
    APP / "core" / "statutory_reference.py",
    APP / "core" / "payroll_engine.py",
]


def _csv_rows() -> list[dict[str, str]]:
    with SEED_CSV.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


@pytest.fixture(scope="module")
def rows() -> list[StatutoryRate]:
    return [StatutoryRate.from_mapping(row) for row in _csv_rows()]


def _one(
    rows: list[StatutoryRate], scheme: str, on: date, period: str = "standard"
) -> StatutoryRate:
    return next(row for row in rates_in_force(rows, scheme, on) if row.rate_period == period)


def _literal(node: ast.expr) -> object:
    """Evaluate the migration's seed literal, allowing only date and Decimal calls."""
    if isinstance(node, ast.Call) and not node.keywords and len(node.args) == 1:
        arg = ast.literal_eval(node.args[0])
        if ast.unparse(node.func) == "date.fromisoformat":
            return date.fromisoformat(arg)
        if ast.unparse(node.func) == "Decimal":
            return Decimal(arg)
    if isinstance(node, ast.List):
        return [_literal(item) for item in node.elts]
    if isinstance(node, ast.Dict):
        return {
            ast.literal_eval(key): _literal(value)  # type: ignore[arg-type]
            for key, value in zip(node.keys, node.values, strict=True)
        }
    return ast.literal_eval(node)


# ------------------------------------------------------------ seed integrity --
def test_migration_seed_matches_the_reviewed_csv(rows: list[StatutoryRate]) -> None:
    tree = ast.parse(MIGRATION.read_text(encoding="utf-8"))
    assign = next(
        node
        for node in tree.body
        if isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "SEED_ROWS"
    )
    assert assign.value is not None
    seeded = _literal(assign.value)
    assert [StatutoryRate.from_mapping(row) for row in seeded] == rows


def test_every_row_has_dates_rule_and_a_gov_uk_source(rows: list[StatutoryRate]) -> None:
    for row in rows:
        assert row.effective_to is not None, f"{row.scheme} {row.rate_period} open-ended"
        assert row.effective_to >= row.effective_from
        assert row.source_reference
        assert row.source_url.startswith("https://www.gov.uk/")
        # keyed to the tax year: the row starts in April of that year
        assert (row.effective_from.year, row.effective_from.month) == (row.tax_year, 4)


def test_no_overlaps_and_no_gaps_between_tax_years(rows: list[StatutoryRate]) -> None:
    by_key: dict[tuple[str, str], list[StatutoryRate]] = {}
    for row in rows:
        by_key.setdefault((row.scheme, row.rate_period), []).append(row)
    for key, series in by_key.items():
        series.sort(key=lambda row: row.effective_from)
        for earlier, later in pairwise(series):
            assert earlier.effective_to is not None
            assert later.effective_from == earlier.effective_to + timedelta(days=1), key


def test_smp_rate_periods_cover_every_week_once(rows: list[StatutoryRate]) -> None:
    smp = rates_in_force(rows, "SMP", date(2026, 7, 1))
    weeks = [w for row in smp for w in range(row.period_start_week, row.period_end_week + 1)]
    assert weeks == list(range(1, smp[0].max_entitlement_weeks + 1))


# ---------------------------------------------------- published 2026/27 values --
def test_2026_27_values_match_hmrc(rows: list[StatutoryRate]) -> None:
    on = date(2026, 6, 1)
    ssp = _one(rows, "SSP", on)
    assert ssp.weekly_flat_rate == Decimal("123.25")
    assert ssp.awe_percentage == Decimal("0.80")
    assert ssp.rate_rule == "lower_of_flat_and_percentage"
    assert ssp.lower_earnings_limit_weekly is None  # removed from 6 April 2026
    assert ssp.waiting_days == 0  # removed from 6 April 2026
    assert ssp.max_entitlement_weeks == 28

    first = _one(rows, "SMP", on, "first_6_weeks")
    rest = _one(rows, "SMP", on, "remaining_weeks")
    assert (first.awe_percentage, first.weekly_flat_rate) == (Decimal("0.90"), None)
    assert (rest.awe_percentage, rest.weekly_flat_rate) == (Decimal("0.90"), Decimal("194.32"))
    assert first.lower_earnings_limit_weekly == Decimal("129.00")
    assert rest.max_entitlement_weeks == 39

    spp = _one(rows, "SPP", on)
    assert spp.weekly_flat_rate == Decimal("194.32")
    assert spp.lower_earnings_limit_weekly == Decimal("129.00")
    assert spp.max_entitlement_weeks == 2
    assert spp.payment_window_weeks == 52
    assert spp.continuous_employment_weeks == 26


def test_smp_uprating_starts_on_the_first_sunday_in_april(rows: list[StatutoryRate]) -> None:
    # HMRC: the SMP rate applies from 5 April 2026; every other rate from 6 April.
    assert _one(rows, "SMP", date(2026, 4, 5), "remaining_weeks").weekly_flat_rate == Decimal(
        "194.32"
    )
    assert _one(rows, "SPP", date(2026, 4, 5)).weekly_flat_rate == Decimal("187.18")


# --------------------------------------------------- resolution by pay period --
def test_a_prior_period_uses_the_values_in_force_at_the_time(rows: list[StatutoryRate]) -> None:
    before = _one(rows, "SSP", date(2026, 3, 31))
    after = _one(rows, "SSP", date(2026, 4, 6))
    assert (before.weekly_flat_rate, before.waiting_days) == (Decimal("118.75"), 3)
    assert before.lower_earnings_limit_weekly == Decimal("125.00")
    assert (after.weekly_flat_rate, after.waiting_days) == (Decimal("123.25"), 0)


def test_a_period_with_no_reference_data_is_refused(rows: list[StatutoryRate]) -> None:
    with pytest.raises(StatutoryReferenceError, match="no SSP reference data in force"):
        rates_in_force(rows, "SSP", date(2027, 4, 6))
    with pytest.raises(StatutoryReferenceError, match="no SMP reference data in force"):
        rates_in_force(rows, "SMP", date(2025, 4, 5))


def test_overlapping_rows_are_refused(rows: list[StatutoryRate]) -> None:
    ssp = _one(rows, "SSP", date(2026, 6, 1))
    with pytest.raises(StatutoryReferenceError, match="overlapping"):
        rates_in_force([ssp, ssp], "SSP", date(2026, 6, 1))


# ---------------------------------------------------------------------- SSP --
def test_ssp_is_the_lower_of_the_flat_rate_and_80_percent(rows: list[StatutoryRate]) -> None:
    ssp = _one(rows, "SSP", date(2026, 6, 1))
    assert weekly_rate(ssp, Decimal("100.00")) == Decimal("80.00")
    assert weekly_rate(ssp, Decimal("400.00")) == Decimal("123.25")


def test_ssp_amounts_match_hmrc_daily_rate_table(rows: list[StatutoryRate]) -> None:
    # HMRC 2026/27 table: 7 qualifying days, 2 days = £35.22; 5 days, 3 days = £73.95.
    ssp = _one(rows, "SSP", date(2026, 6, 1))
    awe = Decimal("500.00")
    assert ssp_daily_rate(ssp, awe, 5) == Decimal("24.65")
    assert ssp_amount(ssp, awe, 7, 2) == Decimal("35.22")
    assert ssp_amount(ssp, awe, 5, 3) == Decimal("73.95")
    assert ssp_amount(ssp, awe, 5, 5) == Decimal("123.25")


def test_ssp_from_day_one_in_2026_27_but_after_waiting_days_before(
    rows: list[StatutoryRate],
) -> None:
    old = _one(rows, "SSP", date(2026, 3, 2))
    new = _one(rows, "SSP", date(2026, 6, 1))
    assert ssp_payable_days(old, 3) == 0
    assert ssp_payable_days(new, 3) == 3
    assert ssp_amount(old, Decimal("500.00"), 5, 3) == Decimal("0.00")
    assert ssp_amount(old, Decimal("500.00"), 5, 5) == Decimal("47.50")  # 2 of 5 days


def test_ssp_earnings_test_applies_before_6_april_2026_only(rows: list[StatutoryRate]) -> None:
    old = _one(rows, "SSP", date(2026, 3, 2))
    new = _one(rows, "SSP", date(2026, 6, 1))
    assert not meets_earnings_test(old, Decimal("100.00"))
    assert meets_earnings_test(new, Decimal("100.00"))
    assert ssp_amount(old, Decimal("100.00"), 5, 10) == Decimal("0.00")
    assert ssp_amount(new, Decimal("100.00"), 5, 5) == Decimal("80.00")


# ---------------------------------------------------------------- SMP / SPP --
def test_smp_schedule_is_six_weeks_at_90_percent_then_the_capped_rate(
    rows: list[StatutoryRate],
) -> None:
    smp = rates_in_force(rows, "SMP", date(2026, 7, 1))
    schedule = weekly_schedule(smp, Decimal("500.00"))
    assert len(schedule) == 39
    assert schedule[:6] == [Decimal("450.00")] * 6
    assert schedule[6:] == [Decimal("194.32")] * 33


def test_smp_low_earner_gets_90_percent_throughout(rows: list[StatutoryRate]) -> None:
    smp = rates_in_force(rows, "SMP", date(2026, 7, 1))
    assert set(weekly_schedule(smp, Decimal("200.00"))) == {Decimal("180.00")}


def test_fractions_of_a_penny_round_up(rows: list[StatutoryRate]) -> None:
    first = _one(rows, "SMP", date(2026, 7, 1), "first_6_weeks")
    assert weekly_rate(first, Decimal("333.33")) == Decimal("300.00")  # 299.997


def test_smp_in_the_prior_year_uses_the_prior_cap(rows: list[StatutoryRate]) -> None:
    smp = rates_in_force(rows, "SMP", date(2026, 3, 1))
    assert weekly_schedule(smp, Decimal("500.00"))[-1] == Decimal("187.18")


def test_spp_two_weeks_inside_the_52_week_window(rows: list[StatutoryRate]) -> None:
    spp = rates_in_force(rows, "SPP", date(2026, 7, 1))
    assert weekly_schedule(spp, Decimal("600.00")) == [Decimal("194.32")] * 2
    assert spp_window_end(spp[0], date(2026, 7, 1)) == date(2027, 6, 29)


def test_parental_eligibility_tests_come_from_the_row(rows: list[StatutoryRate]) -> None:
    spp = _one(rows, "SPP", date(2026, 7, 1))
    assert has_continuous_employment(spp, 26)
    assert not has_continuous_employment(spp, 25)
    assert not meets_earnings_test(spp, Decimal("128.99"))
    assert meets_earnings_test(spp, Decimal("129.00"))
    ewc = date(2026, 11, 1)
    assert qualifying_week_start(spp, ewc) == ewc - timedelta(weeks=15)


# ------------------------------------------------------------ static guard --
def _reference_values() -> set[Decimal]:
    """Every money amount and percentage in the seed, in any year."""
    values: set[Decimal] = set()
    for row in _csv_rows():
        for field in ("weekly_flat_rate", "lower_earnings_limit_weekly", "awe_percentage"):
            if row[field]:
                values.add(Decimal(row[field]).normalize())
    return values


#: Distinctive statutory week counts. Small numbers (2, 3, 6, 8) are too
#: common in ordinary code to scan for; the row-driven tests cover those.
_WEEK_LIMITS = {15, 26, 28, 39, 52}


def test_no_statutory_rate_or_threshold_is_hard_coded() -> None:
    money = _reference_values()
    offenders: list[str] = []
    for path in CALCULATION_MODULES:
        if not path.exists():
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Constant) or isinstance(node.value, bool):
                continue
            value = node.value
            if isinstance(value, int) and value in _WEEK_LIMITS:
                offenders.append(f"{path.name}:{node.lineno} week limit {value}")
            elif isinstance(value, int | float | str):
                try:
                    as_decimal = Decimal(str(value)).normalize()
                except ArithmeticError:
                    continue
                if as_decimal in money:
                    offenders.append(f"{path.name}:{node.lineno} rate {value!r}")
    assert offenders == [], "read these from statutory reference data instead"


def test_the_guard_would_catch_a_hard_coded_rate(tmp_path: Path) -> None:
    sample = tmp_path / "sample.py"
    sample.write_text('from decimal import Decimal\nRATE = Decimal("123.25")\n', encoding="utf-8")
    tree = ast.parse(sample.read_text(encoding="utf-8"))
    found = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value[:1].isdigit()
        and Decimal(node.value).normalize() in _reference_values()
    ]
    assert found == ["123.25"]

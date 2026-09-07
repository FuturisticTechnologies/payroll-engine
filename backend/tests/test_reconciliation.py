"""Pay run reconciliation report (M3-11).

Two things have to hold. The report must tie the stored run totals back to the
sum of the employee lines, to the penny, and refuse to export when they
disagree. And the variance column must flag movement against the previous
comparable period at a threshold the caller chooses.

Everything here is a pure function over mappings, so these run without a
database - which is also how finance runs them at month end.
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from app.core.reconciliation import (
    CSV_HEADER,
    DEFAULT_VARIANCE_THRESHOLD_PCT,
    METRICS,
    ReconciliationReport,
    RunTotals,
    build_report,
    money,
    previous_comparable,
    stored_totals,
    summarise_lines,
    tie_back,
    to_csv,
    to_csv_bytes,
)


def line(
    number: str,
    gross: str,
    deductions: str,
    net: str,
    employer_ni: str = "0.00",
) -> dict[str, object]:
    return {
        "employee_number": number,
        "gross_pay": Decimal(gross),
        "total_deductions": Decimal(deductions),
        "net_pay": Decimal(net),
        "employer_ni": Decimal(employer_ni),
    }


LINES = [
    line("A001", "3000.00", "600.00", "2400.00"),
    line("A002", "2500.50", "500.10", "2000.40"),
    line("A003", "1999.50", "399.90", "1599.60"),
]

RUN = {
    "id": "run-3",
    "pay_period": "2026/27 M03",
    "payment_date": "2026-06-30",
    "currency": "GBP",
    "calculation_version": "m3.1.0",
    "ledger_entry_hash": "a" * 64,
    "employee_count": 3,
    "gross_earnings": Decimal("7500.00"),
    "total_deductions": Decimal("1500.00"),
    "net_pay": Decimal("6000.00"),
}


# ------------------------------------------------------------------ arithmetic


def test_money_refuses_a_float() -> None:
    # The M3-15 guard scans the calculation modules statically. This is the
    # runtime half: a float that reaches the report is a rejected input, not a
    # silently rounded one.
    with pytest.raises(TypeError):
        money(1234.56)


def test_money_accepts_strings_ints_and_none() -> None:
    assert money("10.005") == Decimal("10.01")
    assert money(7) == Decimal("7.00")
    assert money(None) == Decimal("0.00")


def test_lines_sum_to_the_stored_totals() -> None:
    derived = summarise_lines(LINES)
    assert derived.employee_count == 3
    assert derived.gross_pay == Decimal("7500.00")
    assert derived.total_deductions == Decimal("1500.00")
    assert derived.net_pay == Decimal("6000.00")


def test_employer_cost_is_gross_plus_employer_ni() -> None:
    # Employer NI is absent before M5, so employer cost is gross. The column
    # still has to be present and correct, because the report shape does not
    # change between milestones.
    assert summarise_lines(LINES).employer_cost == Decimal("7500.00")

    with_ni = [line("A001", "1000.00", "200.00", "800.00", employer_ni="138.00")]
    assert summarise_lines(with_ni).employer_cost == Decimal("1138.00")


# -------------------------------------------------------------------- tie-back


def test_a_consistent_run_ties_back() -> None:
    report = build_report(RUN, LINES)
    assert report.ties_back
    assert report.disagreements == ()


def test_a_penny_out_is_caught() -> None:
    # One penny on one employee is one penny on fifty thousand payslips.
    broken = {**RUN, "net_pay": Decimal("6000.01")}
    report = build_report(broken, LINES)

    assert not report.ties_back
    assert [d.metric for d in report.disagreements] == ["net_pay"]
    assert report.disagreements[0].difference == Decimal("0.01")


def test_tie_back_checks_every_reported_metric() -> None:
    stored = stored_totals(RUN)
    zeroed = RunTotals(3, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    assert {d.metric for d in tie_back(stored, zeroed)} == set(METRICS)


def test_export_refuses_a_report_that_does_not_tie_back() -> None:
    report = build_report({**RUN, "gross_earnings": Decimal("7499.99")}, LINES)
    with pytest.raises(ValueError, match="does not tie back"):
        to_csv(report)


# -------------------------------------------------------------------- variance


def test_variance_against_the_previous_period() -> None:
    previous = summarise_lines(
        [
            line("A001", "3000.00", "600.00", "2400.00"),
            line("A002", "2500.00", "500.00", "2000.00"),
            line("A003", "1500.00", "300.00", "1200.00"),
        ]
    )
    report = build_report(RUN, LINES, previous=previous)

    gross = next(v for v in report.variances if v.metric == "gross_pay")
    assert gross.previous == Decimal("7000.00")
    assert gross.movement == Decimal("500.00")
    assert gross.movement_pct == Decimal("7.14")
    assert gross.breaches_threshold  # 7.14% >= the 5% default


def test_the_threshold_is_configurable() -> None:
    previous = RunTotals(
        3,
        Decimal("7300.00"),
        Decimal("1460.00"),
        Decimal("5840.00"),
        Decimal("7300.00"),
    )
    # 2.74% movement on gross.
    tight = build_report(RUN, LINES, previous=previous, threshold_pct=Decimal("2.00"))
    loose = build_report(RUN, LINES, previous=previous, threshold_pct=Decimal("10.00"))

    assert [v.metric for v in tight.breaches] == list(METRICS)
    assert loose.breaches == ()


def test_the_default_threshold_is_five_percent() -> None:
    assert Decimal("5.00") == DEFAULT_VARIANCE_THRESHOLD_PCT


def test_a_first_run_reports_an_empty_variance_rather_than_none() -> None:
    report = build_report(RUN, LINES, previous=None)
    assert len(report.variances) == len(METRICS)
    assert all(v.previous is None for v in report.variances)
    assert all(v.movement is None for v in report.variances)
    assert report.breaches == ()


def test_a_zero_previous_period_is_not_an_infinite_rise() -> None:
    previous = RunTotals(0, Decimal("0.00"), Decimal("0.00"), Decimal("0.00"), Decimal("0.00"))
    report = build_report(RUN, LINES, previous=previous)
    gross = next(v for v in report.variances if v.metric == "gross_pay")

    assert gross.movement == Decimal("7500.00")
    assert gross.movement_pct is None
    assert not gross.breaches_threshold


def test_previous_comparable_walks_back_one_period() -> None:
    runs = [{"id": "run-1"}, {"id": "run-2"}, {"id": "run-3"}]
    lines_by_run = {"run-1": [], "run-2": LINES, "run-3": LINES}

    previous = previous_comparable(runs, lines_by_run, "run-3")
    assert previous is not None
    assert previous.gross_pay == Decimal("7500.00")

    # A first run has nothing behind it, and that is not an error.
    assert previous_comparable(runs, lines_by_run, "run-1") is None
    assert previous_comparable(runs, lines_by_run, "unknown") is None


# ---------------------------------------------------------------------- export


def _report() -> ReconciliationReport:
    previous = RunTotals(
        3,
        Decimal("7000.00"),
        Decimal("1400.00"),
        Decimal("5600.00"),
        Decimal("7000.00"),
    )
    return build_report(RUN, LINES, previous=previous)


def test_csv_has_one_row_per_metric_and_a_header() -> None:
    rows = to_csv(_report()).strip().split("\n")
    assert len(rows) == len(METRICS) + 1
    assert rows[0] == ",".join(f'"{column}"' for column in CSV_HEADER)


def test_csv_quotes_every_field_and_uses_two_decimal_places() -> None:
    body = to_csv(_report())
    assert '"gross_pay","7500.00","7000.00","500.00","7.14","Y"' in body
    # No thousands separators, no scientific notation.
    assert "7,500" not in body
    assert "E+" not in body


def test_csv_bytes_carry_a_bom_because_finance_opens_these_in_excel() -> None:
    assert to_csv_bytes(_report()).startswith(b"\xef\xbb\xbf")


def test_an_empty_run_still_exports() -> None:
    # A missing file is indistinguishable from a forgotten one.
    empty_run = {
        **RUN,
        "employee_count": 0,
        "gross_earnings": Decimal("0.00"),
        "total_deductions": Decimal("0.00"),
        "net_pay": Decimal("0.00"),
    }
    report = build_report(empty_run, [])
    assert report.ties_back
    assert len(to_csv(report).strip().split("\n")) == len(METRICS) + 1

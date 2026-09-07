"""Pay run reconciliation report for finance.

Finance reconciles a pay run against the general ledger at month end. Two
questions decide whether they can: does the run tie back to itself, and what
moved since the last comparable period.

**Tie-back.** Every figure on a pay run exists twice - once as the stored
total on ``pay_runs``, and once as the sum of ``payroll_run_lines``. They are
written by the same engine but by different code paths, so they are genuinely
independent evidence. This module computes both and reports them side by side.
A report where they disagree is not a report: :func:`build_report` marks it and
:func:`to_csv` refuses to write it. A reconciliation document that is
internally inconsistent is worse than no document, because somebody will
reconcile against it.

**Variance.** Movement against the previous comparable period, with a
threshold so the eye goes to the four rows that moved rather than the four
hundred that did not. The threshold is a parameter, not a constant: a payroll
growing 3% a month and a flat one do not want the same number.

Pure functions over plain mappings, like :mod:`app.core.ledger_verify`. They
run against a database export, an API response or a test fixture without a
session, which is what makes them usable from a script at month end.
"""
from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

#: Movement at or above this percentage is flagged. Overridable per call.
DEFAULT_VARIANCE_THRESHOLD_PCT = Decimal("5.00")

PENNY = Decimal("0.01")
ZERO = Decimal("0.00")

#: The figures finance reconciles, in the order they are reported. Employer
#: cost sits last and outside the payslip arithmetic on purpose - it is not a
#: deduction, and presenting it as one is the most common way these reports
#: get misread.
METRICS: tuple[str, ...] = (
    "gross_pay",
    "total_deductions",
    "net_pay",
    "employer_cost",
)


def money(value: Any) -> Decimal:
    """Coerce to a 2dp Decimal without ever passing through a float."""
    if isinstance(value, Decimal):
        amount = value
    elif isinstance(value, float):
        raise TypeError("money must not be constructed from a float")
    else:
        amount = Decimal(str(value if value is not None else "0"))
    return amount.quantize(PENNY, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RunTotals:
    """The four figures, plus the headcount they were computed over."""

    employee_count: int
    gross_pay: Decimal
    total_deductions: Decimal
    net_pay: Decimal
    employer_cost: Decimal

    def get(self, metric: str) -> Decimal:
        value: Decimal = getattr(self, metric)
        return value


@dataclass(frozen=True)
class Disagreement:
    """One metric where the stored total and the summed lines differ."""

    metric: str
    stored: Decimal
    derived: Decimal

    @property
    def difference(self) -> Decimal:
        return self.stored - self.derived

    def __str__(self) -> str:
        return (
            f"{self.metric}: stored {self.stored} vs lines {self.derived} "
            f"(difference {self.difference})"
        )


@dataclass(frozen=True)
class Variance:
    """Movement in one metric against the previous comparable period."""

    metric: str
    current: Decimal
    previous: Decimal | None
    threshold_pct: Decimal

    @property
    def movement(self) -> Decimal | None:
        if self.previous is None:
            return None
        return self.current - self.previous

    @property
    def movement_pct(self) -> Decimal | None:
        """Percentage movement, or ``None`` where it has no meaning.

        A previous period of zero is not a 100% rise, it is a first period.
        Reporting infinity there trains people to ignore the column.
        """
        movement = self.movement
        if movement is None or self.previous is None or self.previous == ZERO:
            return None
        return (movement / self.previous * Decimal("100")).quantize(
            PENNY, rounding=ROUND_HALF_UP
        )

    @property
    def breaches_threshold(self) -> bool:
        pct = self.movement_pct
        if pct is None:
            return False
        return abs(pct) >= self.threshold_pct


@dataclass(frozen=True)
class ReconciliationReport:
    pay_run_id: str
    pay_period: str
    payment_date: str
    currency: str
    calculation_version: str
    ledger_entry_hash: str | None
    stored: RunTotals
    derived: RunTotals
    disagreements: tuple[Disagreement, ...]
    variances: tuple[Variance, ...]

    @property
    def ties_back(self) -> bool:
        return not self.disagreements

    @property
    def breaches(self) -> tuple[Variance, ...]:
        return tuple(v for v in self.variances if v.breaches_threshold)


def _employer_cost(row: Mapping[str, Any]) -> Decimal:
    """Gross plus employer NI.

    Employer NI arrives in M5. Before then the column is absent rather than
    zero, and defaulting it keeps this readable against every milestone
    snapshot without a version check.
    """
    return money(row.get("gross_pay", 0)) + money(row.get("employer_ni", 0))


def summarise_lines(lines: Iterable[Mapping[str, Any]]) -> RunTotals:
    """Sum the employee lines. One of the two independent sources."""
    rows = list(lines)
    return RunTotals(
        employee_count=len(rows),
        gross_pay=sum((money(r.get("gross_pay", 0)) for r in rows), ZERO),
        total_deductions=sum(
            (money(r.get("total_deductions", 0)) for r in rows), ZERO
        ),
        net_pay=sum((money(r.get("net_pay", 0)) for r in rows), ZERO),
        employer_cost=sum((_employer_cost(r) for r in rows), ZERO),
    )


def stored_totals(run: Mapping[str, Any]) -> RunTotals:
    """Read the totals held on the pay run. The other independent source."""
    gross = money(run.get("gross_earnings", 0))
    return RunTotals(
        employee_count=int(run.get("employee_count", 0) or 0),
        gross_pay=gross,
        total_deductions=money(run.get("total_deductions", 0)),
        net_pay=money(run.get("net_pay", 0)),
        employer_cost=gross + money(run.get("employer_ni", 0)),
    )


def tie_back(stored: RunTotals, derived: RunTotals) -> tuple[Disagreement, ...]:
    """Every metric where the two sources disagree, to the penny."""
    return tuple(
        Disagreement(
            metric=metric, stored=stored.get(metric), derived=derived.get(metric)
        )
        for metric in METRICS
        if stored.get(metric) != derived.get(metric)
    )


def build_report(
    run: Mapping[str, Any],
    lines: Iterable[Mapping[str, Any]],
    *,
    previous: RunTotals | None = None,
    threshold_pct: Decimal = DEFAULT_VARIANCE_THRESHOLD_PCT,
) -> ReconciliationReport:
    """Build the report for one pay run.

    ``previous`` is the totals of the previous comparable period, or ``None``
    for a first run - in which case the variance columns are present but
    empty, rather than absent. Finance reads the same shape every month.
    """
    derived = summarise_lines(lines)
    stored = stored_totals(run)
    return ReconciliationReport(
        pay_run_id=str(run.get("id", "")),
        pay_period=str(run.get("pay_period", "")),
        payment_date=str(run.get("payment_date", "")),
        currency=str(run.get("currency", "GBP")),
        calculation_version=str(run.get("calculation_version", "")),
        ledger_entry_hash=run.get("ledger_entry_hash"),
        stored=stored,
        derived=derived,
        disagreements=tie_back(stored, derived),
        variances=tuple(
            Variance(
                metric=metric,
                current=derived.get(metric),
                previous=previous.get(metric) if previous is not None else None,
                threshold_pct=threshold_pct,
            )
            for metric in METRICS
        ),
    )


def _fmt(value: Decimal | None) -> str:
    """Two decimal places, no separators, never scientific notation."""
    if value is None:
        return ""
    return f"{value.quantize(PENNY, rounding=ROUND_HALF_UP):f}"


CSV_HEADER: tuple[str, ...] = (
    "pay_run_id",
    "pay_period",
    "payment_date",
    "metric",
    "current",
    "previous",
    "movement",
    "movement_pct",
    "over_threshold",
    "currency",
    "calculation_version",
    "ledger_entry_hash",
)


def to_csv(report: ReconciliationReport) -> str:
    """Render the summary for the finance spreadsheet.

    Every field is quoted because period labels and hashes travel through
    spreadsheets that would otherwise reinterpret them.

    Refuses to render a report that does not tie back. See the module
    docstring: the failure has to surface here, not in a spreadsheet.
    """
    if not report.ties_back:
        raise ValueError(
            "pay run does not tie back, refusing to export: "
            + "; ".join(str(d) for d in report.disagreements)
        )

    buffer = io.StringIO()
    writer = csv.writer(buffer, quoting=csv.QUOTE_ALL, lineterminator="\n")
    writer.writerow(CSV_HEADER)
    for variance in report.variances:
        writer.writerow(
            [
                report.pay_run_id,
                report.pay_period,
                report.payment_date,
                variance.metric,
                _fmt(variance.current),
                _fmt(variance.previous),
                _fmt(variance.movement),
                _fmt(variance.movement_pct),
                "Y" if variance.breaches_threshold else "N",
                report.currency,
                report.calculation_version,
                report.ledger_entry_hash or "",
            ]
        )
    return buffer.getvalue()


def to_csv_bytes(report: ReconciliationReport) -> bytes:
    """The file finance actually opens: UTF-8 **with** a BOM, because Excel."""
    return to_csv(report).encode("utf-8-sig")


def previous_comparable(
    runs: Sequence[Mapping[str, Any]],
    lines_by_run: Mapping[str, Sequence[Mapping[str, Any]]],
    current_run_id: str,
) -> RunTotals | None:
    """Totals of the run immediately before ``current_run_id``.

    "Comparable" means the previous period of the same frequency, which is
    what ``runs`` is expected to hold, ordered oldest first. Returns ``None``
    for the first run rather than raising: a first period is a normal state,
    not an error.
    """
    ids = [str(run.get("id", "")) for run in runs]
    try:
        index = ids.index(current_run_id)
    except ValueError:
        return None
    if index == 0:
        return None
    return summarise_lines(lines_by_run.get(ids[index - 1], []))

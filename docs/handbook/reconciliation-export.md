# Pay run reconciliation export

Owner: Data Analyst. Companion to `docs/03-data-model.md`.

Finance does not reconcile against the API. They reconcile in a spreadsheet,
against the general ledger, at month end. This specifies the one export format
that supports that, so we stop producing a slightly different CSV every time
somebody is asked for one.

## 1. What it must answer

Three questions, in this order. Everything in the format exists to answer one
of them:

1. **Does the pay run total agree with what was posted to the GL?**
2. **If it does not, which employee accounts for the difference?**
3. **For that employee, where did the figure come from?**

A format that answers 1 but not 3 sends the query back to us, which is the
situation this replaces.

## 2. Grain

One row per **employee per pay run**, plus one **control row** per pay run.

Not one row per line item. Line items are the answer to question 3 and belong
in the drill-down export, because putting them in the main file makes the row
count vary with how many adjustments were keyed and breaks the subtotal that
finance is actually checking.

## 3. Columns

| # | Column | Source | Notes |
|---|---|---|---|
| 1 | `pay_run_id` | `pay_runs.id` | UUID, quoted |
| 2 | `pay_period` | `pay_periods.tax_year` + `period_number` | e.g. `2026/27 M03` |
| 3 | `payment_date` | `pay_periods.payment_date` | ISO 8601 |
| 4 | `employee_number` | `payroll_run_lines.employee_number` | Employer's own numbering |
| 5 | `employee_name` | `payroll_run_lines.employee_name` | As at calculation time |
| 6 | `base_salary` | `payroll_run_lines.base_salary` | |
| 7 | `additional_earnings` | `payroll_run_lines.additional_earnings` | |
| 8 | `gross_pay` | `payroll_run_lines.gross_pay` | 6 + 7 |
| 9 | `paye_tax` | `payroll_run_lines.paye_tax` | Zero before M4 |
| 10 | `employee_ni` | `payroll_run_lines.employee_ni` | Zero before M5 |
| 11 | `other_deductions` | derived | 12 − 9 − 10 |
| 12 | `total_deductions` | `payroll_run_lines.total_deductions` | |
| 13 | `net_pay` | `payroll_run_lines.net_pay` | 8 − 12 |
| 14 | `employer_ni` | `payroll_run_lines.employer_ni` | Employer cost, not a deduction |
| 15 | `currency` | | `GBP` |
| 16 | `calculation_version` | `pay_runs.calculation_version` | Which engine produced this |
| 17 | `ledger_entry_hash` | `pay_runs.ledger_entry_hash` | Ties the row to the ledger |

`employer_ni` sits deliberately after `net_pay`. It is not part of the
employee's payslip arithmetic and putting it inside the deduction columns is
the single most common way these exports get misread.

## 4. The control row

Last row of each pay run, with `employee_number` set to `TOTAL`:

- Columns 6–14 are the **sum of the employee rows**.
- They are *also* the values held on `pay_runs`.

Those are two independent sources, and the export writes both. If they
disagree the export must fail rather than emit a file — a reconciliation
document that is internally inconsistent is worse than no document, because
somebody will reconcile against it.

## 5. Rules

- **Decimal formatting**: two decimal places, no thousands separator, `.` as
  the decimal point. Never scientific notation.
- **Encoding**: UTF-8 with BOM. Excel misreads UTF-8 without it, and finance
  opens these in Excel.
- **Quoting**: all fields quoted. Employee names contain commas.
- **Ordering**: by `employee_number`, ascending, as a string — employers use
  numbers like `A001`.
- **Empty runs**: still export, with a control row of zeroes. A missing file is
  indistinguishable from a forgotten one.

## 6. Integrity

Every export carries `ledger_entry_hash`. That value is reproducible from the
ledger with `app.core.ledger_verify`, so a spreadsheet that has been edited can
be checked back against the immutable record:

```python
from app.core.ledger_verify import verify_rows
verdict = verify_rows(entries)   # entries for the tenant, any order
assert verdict.is_intact, str(verdict)
```

This is the reason the hash is on the row at all. Without it the export is a
claim; with it, it is evidence.

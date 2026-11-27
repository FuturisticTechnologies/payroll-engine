# Statutory reference data: analyst pack

SNOV-442. Review and reporting files for the SSP, SMP and SPP rates in
`statutory_payment_rates`. The data itself lives in
`backend/app/reference_data/statutory_payment_rates.csv`. Nothing here is read
by the application.

| File | Use |
|---|---|
| `statutory_payment_rates_review.xlsx` | Review workbook: the rates, a calculator, year-on-year changes, and PASS/FAIL checks |
| `build_review_workbook.py` | Regenerates the workbook from the CSV (`pip install openpyxl`) |
| `sql/statutory_reference_checks.sql` | Postgres queries: in force on a date, overlap, gap, missing input and source checks, year on year |
| `powerbi/` | Power Query and DAX for the Power BI report, with build steps |

Background, sources and the annual update process:
[`docs/handbook/statutory-reference-data.md`](../../docs/handbook/statutory-reference-data.md).

# Statutory payment reference data

SNOV-442 · Owner: Data Analyst · Added: M8

SSP, SMP and SPP are calculated from effective-dated rows in
`statutory_payment_rates`, never from constants in code. This page says what
is in the table, where each value came from, how the engine picks a row, and
how to add the next tax year.

## 1. What is seeded

Two tax years, so that a pay run for a period before 6 April 2026 still uses
the values in force at the time.

| Scheme | Rate period | Weeks | From | To | % of AWE | Weekly flat rate | Rule | LEL (weekly) | Waiting days | Max weeks | Service test | Window |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SSP | standard | 1–28 | 2025-04-06 | 2026-04-05 | – | £118.75 | flat rate only | £125.00 | 3 | 28 | – | – |
| SMP | first_6_weeks | 1–6 | 2025-04-06 | 2026-04-04 | 90% | – | percentage only | £125.00 | 0 | 39 | 26 weeks | – |
| SMP | remaining_weeks | 7–39 | 2025-04-06 | 2026-04-04 | 90% | £187.18 | lower of | £125.00 | 0 | 39 | 26 weeks | – |
| SPP | standard | 1–2 | 2025-04-06 | 2026-04-05 | 90% | £187.18 | lower of | £125.00 | 0 | 2 | 26 weeks | 52 weeks |
| SSP | standard | 1–28 | 2026-04-06 | 2027-04-05 | 80% | £123.25 | lower of | **none** | **0** | 28 | – | – |
| SMP | first_6_weeks | 1–6 | 2026-04-05 | 2027-04-03 | 90% | – | percentage only | £129.00 | 0 | 39 | 26 weeks | – |
| SMP | remaining_weeks | 7–39 | 2026-04-05 | 2027-04-03 | 90% | £194.32 | lower of | £129.00 | 0 | 39 | 26 weeks | – |
| SPP | standard | 1–2 | 2026-04-06 | 2027-04-05 | 90% | £194.32 | lower of | £129.00 | 0 | 2 | 26 weeks | 52 weeks |

All rows: AWE relevant period of 8 weeks. Payments round **up** to the next
penny. For SMP and SPP the qualifying week is the 15th week before the
expected week of childbirth.

### What changed on 6 April 2026

The Employment Rights Act 2025 changed SSP from 6 April 2026:

- **No waiting days.** SSP is paid from the first qualifying day of sickness (it was the fourth).
- **No lower earnings limit.** Every eligible employee qualifies, whatever they earn.
- **80% cap.** SSP is £123.25 or 80% of average weekly earnings, whichever is lower.

None of this is an `if date >= 2026-04-06` in code. It is the difference
between the 2025 and 2026 SSP rows, which is why a March 2026 absence still
gets three waiting days and the old earnings test.

Paternity *leave* became a day-one right on the same date, but the 26-week
service test for Statutory Paternity *Pay* did not change.

### Why SMP has a different start date

The SMP rate changes on the first Sunday in April (5 April 2026), not on
6 April. HMRC's 2026 to 2027 rates page says so explicitly. The SMP rows
therefore run Sunday to Saturday (2026-04-05 to 2027-04-03), and the SMP
row for 2026/27 is keyed to `tax_year = 2026` even though it starts one day
before that tax year does.

## 2. Sources

Every row stores `source_reference` and `source_url`. When someone asks in
two years why a 2026/27 run used a particular figure, the answer is in the row.

- [Rates and thresholds for employers 2026 to 2027](https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027) (HMRC)
- [Rates and thresholds for employers 2025 to 2026](https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026) (HMRC)
- [Sickness absences that start before and end on or after 6 April 2026](https://www.gov.uk/guidance/sickness-absences-that-start-before-and-end-on-or-after-6-april-2026) (HMRC)
- [Statutory Paternity Pay and Leave: employer guide](https://www.gov.uk/employers-paternity-pay-leave/eligibility)

## 3. How the engine uses it

```python
from app.core.statutory_reference import load_statutory_rates
from app.core.statutory_pay import weekly_schedule, ssp_amount

rates = await load_statutory_rates(db, "SMP", period.period_end)   # pay date, not today
schedule = weekly_schedule(rates, average_weekly_earnings)
```

- **Select by the date being paid for.** Pass the pay period date or the
  absence or leave week, never `date.today()`. That is the whole of the
  "a prior period uses the values in force then" rule.
- **No row, no payment.** If nothing is in force for the date, or two rows
  overlap, `StatutoryReferenceError` is raised. The engine does not fall back
  to another year's rate.
- **No rate in code.** `tests/test_statutory_reference.py` scans the
  calculation modules and fails if any seeded rate, threshold, percentage or
  distinctive week limit appears as a literal.

## 4. Where the data lives

| File | Role |
|---|---|
| `backend/app/reference_data/statutory_payment_rates.csv` | The reviewed source. Edit this first. |
| `backend/app/db/migrations/versions/20261127_0008_m8_statutory_payment_reference_data.py` | Seeds Postgres. Rows are frozen inline; a test checks they match the CSV. |
| `backend/app/core/statutory_reference.py` | Loads rows by date; seeds local SQLite from the CSV. |
| `backend/app/core/statutory_pay.py` | Pure rules that read the rows. |
| `analytics/statutory-reference/` | Excel review workbook, SQL checks and Power BI files for the analyst. |

## 5. Adding the next tax year

1. Wait for HMRC's *Rates and thresholds for employers* page for the new year.
   Proposed DWP rates are not enough.
2. Add the new rows to the CSV with sources. Leave the old rows alone, because
   they are history.
3. Open `analytics/statutory-reference/statutory_payment_rates_review.xlsx`,
   paste the CSV into **Rates**, and check that every row on **Checks** says PASS.
4. Write a **new** Alembic revision that inserts only the new rows. Never edit
   `20261127_0008`, since `scripts/check-migrations.sh` blocks it.
5. Update the expected figures in `test_statutory_reference.py` from the HMRC
   page, not from the CSV.
6. Get a second person to review the figures against the HMRC page before
   merging (SNOV-310 review step).

## 6. Not covered here

SAP, ShPP, SPBP and SNCP rates, and SMP/SPP recovery rates (92% / 109%,
£45,000 Class 1 NI threshold), are published on the same HMRC page but are
not seeded by SNOV-442.

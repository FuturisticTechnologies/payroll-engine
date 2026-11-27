# Power BI: statutory reference data

SNOV-442. Files to build the **Statutory rates** report in Power BI Desktop.
There's no `.pbix` here: it is a binary that cannot be reviewed in a pull
request, so the query and measures are kept as text and the report is built
from them.

| File | What it is |
|---|---|
| `StatutoryRates.pq` | Power Query that loads the rates from the reviewed CSV or from Postgres |
| `StatutoryRates.dax` | `Calendar` table and the measures |

## Build it (about 10 minutes)

1. **Parameters:** in *Home → Transform data → Manage parameters*, add
   `SourceMode` (`csv`) and `StatutoryRatesCsv` (full path to
   `backend/app/reference_data/statutory_payment_rates.csv`). For Postgres,
   set `SourceMode` to `postgres` and add `PgServer` and `PgDatabase`.
2. **Query:** create a *Blank query* named `StatutoryRates`, open the Advanced
   Editor and paste `StatutoryRates.pq`.
3. **Calendar:** in *Modeling → New table*, paste the `Calendar` definition.
   Leave it unrelated to `StatutoryRates`.
4. **Measures:** add each measure from `StatutoryRates.dax` to `StatutoryRates`.
   Format `AWE % In Force` as a percentage and the money measures as £ currency.
5. **What-if:** add *Modeling → New parameter → Numeric range* named `AWE`
   (0 to 1,000, step 10, default 500) for `Example Weekly Amount`.

## Suggested pages

- **In force on a date:** a date slicer on `'Calendar'[Date]` (single value),
  a table of `scheme`, `rate_period` and the *In Force* measures, with a card
  for `Coverage Status`. Move the slicer across 5–6 April 2026 to see SMP
  change a day before SSP and SPP, and SSP lose its waiting days and LEL.
- **Year on year:** a matrix with `scheme_period` on rows, `tax_year_label`
  on columns and `weekly_flat_rate`, plus `Flat Rate Change %`.
- **Timeline:** a Gantt or bar of `effective_from` to `effective_to` by
  `scheme_period`. Gaps or overlaps show up immediately.
- **Sources:** a table of `scheme_period`, `tax_year_label` and `source_url`
  (Data category: Web URL).

The report reads reference data only. It contains no employee data, so it can
be shared with the whole payroll team.

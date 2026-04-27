# 05 — HMRC compliance

PayrollFuturistic is a UK-only product. Every calculation, submission and
statutory payment is anchored to HMRC's rules for the current and previous
tax years.

## 1. Scope of HMRC obligations

| Area | Capability | Landing milestone |
|---|---|---|
| PAYE income tax | Tax code handling, weekly/monthly, cumulative/non-cumulative | M4 |
| National Insurance | Class 1 primary & secondary, categories A–X | M5 |
| RTI — FPS | Full Payment Submission per pay run | M6 |
| RTI — EPS | Employer Payment Summary, including no-pay periods | M7 |
| RTI — corrections | Earlier Year Update (EYU) / year-to-date adjustments | M7 |
| Statutory payments | SSP, SMP, SPP eligibility + payment | M8 |
| Pension auto-enrolment | Assessment + contribution calculation | M9 |
| Year-end | P60 for active employees, P45 for leavers | M10 |
| Tax tables refresh | Annual refresh pipeline, effective-dated | Continuous |

## 2. Tax codes handled

| Code pattern | Meaning | Treatment |
|---|---|---|
| `1257L`, `####L` | Standard personal allowance | Apply allowance, cumulative by default |
| `BR` | Basic rate on all income | Flat 20% |
| `D0` / `D1` | Higher / additional rate on all | Flat 40% / 45% |
| `NT` | No tax | No PAYE deducted |
| `0T` | No allowance | All income taxed from first £ |
| `K####` | Negative allowance | Reverse adjustment, capped at 50% cap |
| `####L M1/W1 /X` | Non-cumulative (emergency) | Period-only calculation |

Milestone 1 validates the *format* of tax codes at the schema layer.
Behaviour lands with the PAYE engine in M4.

## 3. NI categories

| Category | Description |
|---|---|
| A | Standard |
| B | Married women / widows reduced rate |
| C | Over state pension age |
| H | Apprentice under 25 |
| J | Deferred (has another job) |
| M | Under 21 |
| V | Veterans first 12 months |
| X | No NI payable |
| Z | Deferred, under 21 |

These become the `ni_categories` reference table in M5.

## 4. RTI submission envelope

FPS and EPS submissions will be generated as HMRC-compliant XML envelopes,
signed and transmitted via the HMRC Transaction Engine API.

Key design decisions:

- One `rti_submissions` row per envelope, with `status` in
  `{pending, submitted, accepted, rejected, errored}`.
- Every transition is audit-logged.
- Outbound calls go through a circuit breaker with exponential backoff.
- HMRC OAuth credentials live in Vault, never in the database or logs.
- All PII in RTI envelopes is redacted from logs.

## 5. Statutory payments — eligibility and caps

Full rule tables arrive with the calculation engines. Placeholder rules:

- **SSP** — up to 28 weeks; qualifying day rules; waiting days 1–3;
  minimum 4 consecutive days of incapacity; earnings threshold check.
- **SMP** — 39 weeks; 90% of AWE for first 6 weeks, then lower of 90% AWE
  or statutory flat rate for 33 weeks.
- **SPP** — up to 2 weeks at statutory rate; continuous-employment test.

## 6. Year-end deliverables

| Artefact | Trigger |
|---|---|
| P60 | For employees active at 5 April |
| P45 | On leaver event |
| FPS final | Marked as "Final submission for tax year" |

## 7. Tax year and period handling

- UK tax year: 6 April – 5 April.
- Pay frequency supported: weekly, two-weekly, four-weekly, monthly.
- Tax week / tax month is computed from the tax year start.
- Every monetary calculation records the `tax_year`, `tax_period_type` and
  `tax_period_number` against the output row — enabling full reconciliation.

## 8. Testing strategy for HMRC logic

- Deterministic golden-path tests with fixed inputs and expected outputs,
  sourced from HMRC's published calculation examples.
- Property-based tests via Hypothesis: gross pay ≥ net pay, monotonicity,
  idempotency of pay runs with identical inputs.
- Regression pack covering every tax year released.
- End-to-end RTI dry-run against the HMRC sandbox before every prod deploy.

# 05 - HMRC Compliance

PayrollFuturistic is a UK-only payroll product. Every calculation, submission
and statutory payment is anchored to HMRC rules for the relevant tax year.

## 1. Scope of HMRC Obligations

| Area | Capability | Landing milestone |
|---|---|---|
| PAYE income tax | Tax code handling, weekly/monthly and cumulative/non-cumulative logic | M4 |
| National Insurance | Class 1 primary/secondary, categories and director rules | M5 |
| RTI FPS | Full Payment Submission per pay run | M6 |
| RTI EPS | Employer Payment Summary, including no-pay periods | M7 |
| RTI corrections | Year-to-date adjustments and reconciliation | M7 |
| Statutory payments | SSP, SMP and SPP eligibility and payment | M8 |
| Pension auto-enrolment | Assessment and contribution calculation | M9 |
| Year-end | P60 for active employees, P45 for leavers | M10 |
| Tax table refresh | Annual effective-dated reference update | Continuous |

## 2. Tax Codes Handled

| Code pattern | Meaning | Treatment |
|---|---|---|
| `1257L`, `####L` | Standard personal allowance | Apply allowance, cumulative by default |
| `BR` | Basic rate on all income | Flat 20% |
| `D0` / `D1` | Higher / additional rate on all income | Flat 40% / 45% |
| `NT` | No tax | No PAYE deducted |
| `0T` | No allowance | All income taxed from first pound |
| `K####` | Negative allowance | Reverse adjustment, capped by HMRC rules |
| `####L M1/W1/X` | Non-cumulative emergency treatment | Period-only calculation |

Current implementation validates tax-code format at the schema layer. PAYE
behaviour lands with the calculation engine in M4.

## 3. NI Categories

Milestone 2 stores `ni_category` on employees and exposes category reference
data through `/api/v1/framework`.

| Category | Description |
|---|---|
| A | Standard employee |
| B | Married women and widows reduced rate |
| C | Employees over State Pension age |
| H | Apprentice under 25 |
| J | Employee can defer National Insurance |
| M | Employee under 21 |
| V | Veteran in first civilian job |
| Z | Employee under 21 can defer National Insurance |

The M5 calculation milestone expands this into annual effective-dated NI
reference data and contribution rules.

## 4. Pay Frequencies

Milestone 2 supports payroll framework setup for:

- Weekly, 52 periods per tax year.
- Fortnightly, 26 periods per tax year.
- Four-weekly, 13 periods per tax year.
- Monthly, 12 periods per tax year.

These frequencies are stored on tenants as a default and on employment
contracts as the calculation basis for later pay runs.

## 5. RTI Submission Envelope

FPS and EPS submissions will be generated as HMRC-compliant envelopes,
transmitted via HMRC APIs and tracked with full audit history.

Design rules:

- One `rti_submissions` row per outbound envelope.
- Status lifecycle: pending, submitted, accepted, rejected, errored.
- Every status transition is audit-logged.
- Outbound calls use retry, backoff and reconciliation.
- HMRC OAuth credentials live in a vault, never in source control or logs.
- PII in RTI payloads is redacted from application logs.

## 6. Statutory Payments

Full rule tables arrive with the calculation engines. The planned coverage is:

- SSP: qualifying days, waiting days, earnings threshold and 28-week cap.
- SMP: average weekly earnings, 90% first period and statutory flat-rate period.
- SPP: qualifying relationship, employment test and statutory rate.

## 7. Year-End Deliverables

| Artefact | Trigger |
|---|---|
| P60 | Employee active at 5 April |
| P45 | Employee leaver event |
| FPS final | Final submission for tax year |

## 8. Tax Year and Period Handling

- UK tax year: 6 April to 5 April.
- Every calculation records tax year, period type and period number.
- Monetary outputs use decimal fixed precision and are reconciliation-friendly.

## 9. Testing Strategy for HMRC Logic

- Golden-path tests from HMRC examples.
- Property-based tests for invariants such as gross pay >= net pay.
- Regression pack per tax year.
- RTI sandbox dry-run before production submission support is enabled.

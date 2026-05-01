# 03 — Data model

Milestone 1 establishes a minimum, typed data model that later milestones
extend. No monetary tables land in this milestone — they arrive together
with the calculation engines that populate them.

## 1. Entity overview

```
┌───────────┐       ┌────────────┐       ┌────────────┐
│   users   │       │ employees  │       │ audit_logs │
└───────────┘       └────────────┘       └────────────┘
      │                   │                    ▲
      │  actor            │  entity            │
      └───────────────────┴────────────────────┘
```

## 2. `users`

Application users: operators, payroll officers, employer admins, employees
(self-service).

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | PK, `gen_random_uuid()` |
| `email` | `citext` | unique, case-insensitive |
| `full_name` | `varchar(255)` | |
| `hashed_password` | `varchar(255)` | bcrypt |
| `role` | `varchar(32)` | `viewer` by default — replaced by RBAC in M2 |
| `is_active` | `boolean` | |
| `is_superuser` | `boolean` | |
| `created_at` | `timestamptz` | server default `now()` |
| `updated_at` | `timestamptz` | auto-updated |

Indexes: `ix_users_email`, `uq_users_email`.

## 3. `employees`

The payroll record for a person paid by an employer. Pay-affecting components
land in later migrations.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | PK |
| `first_name` | `varchar(100)` | |
| `last_name` | `varchar(100)` | |
| `email` | `citext` | unique |
| `national_insurance_number` | `varchar(9)` | unique, HMRC format `AA123456A` |
| `tax_code` | `varchar(10)` | default `1257L` |
| `employment_start_date` | `date` | |
| `job_title` | `varchar(150)` | nullable |
| `created_at` / `updated_at` | `timestamptz` | |

Indexes: `ix_employees_email`, `ix_employees_ni_number`, unique constraints
on both.

Validation at the schema layer:

- NI number matches `^[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$`, upper-cased and
  whitespace-stripped on ingress.
- Tax code matches common UK patterns: `1257L`, `BR`, `D0`, `D1`, `NT`,
  K-codes and numeric suffix codes.

## 4. `audit_logs`

Append-only, immutable. Rows describe *what happened*, *who caused it*,
*when* and *what context was attached*.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | PK |
| `occurred_at` | `timestamptz` | indexed |
| `actor_user_id` | `uuid` | nullable (system events), indexed |
| `actor_ip` | `varchar(45)` | IPv6-capable |
| `event_type` | `varchar(100)` | e.g. `employee.created`, indexed |
| `entity_type` | `varchar(100)` | e.g. `employee` |
| `entity_id` | `varchar(100)` | string-form of the affected entity PK, indexed |
| `payload` | `jsonb` | arbitrary structured context, default `{}` |

Operational rules:

- Writes only. Never updated or deleted via application code.
- Retention: 7 years (to cover HMRC investigation windows).
- Archived to cold storage after 12 months (Milestone 12+).

## 5. Upcoming entities (post-M1 preview)

These are **not** present in the initial migration but are planned so the
current schema does not block them:

- `tenants` — employer organisations (introduces tenant_id everywhere)
- `employment_contracts` — salary, hours, frequency, start/end
- `pay_periods` — tax year / pay frequency calendar
- `pay_runs` — a processed period for a tenant
- `payslips` — per-employee output of a pay run
- `deductions`, `earnings_lines`, `pension_contributions`
- `tax_codes_history` — audit of tax code changes per employee
- `ni_categories` — reference table refreshed annually
- `statutory_payments` — SSP, SMP, SPP instances
- `rti_submissions` — FPS / EPS envelope + HMRC response
- `hmrc_credentials` — per-tenant OAuth tokens (encrypted at rest)

## 6. Money & decimals — rule

All monetary columns will be `NUMERIC(14, 2)`. All rates are `NUMERIC(6, 4)`.
The code base will ban float arithmetic on money via lint rule in M2.

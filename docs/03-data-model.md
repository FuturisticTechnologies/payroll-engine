# 03 - Data Model

Milestone 2 establishes the core employer, employee, RBAC and payroll framework
models needed before the payroll calculation engine begins.

## 1. Entity Overview

```text
tenants
  |-- employees
  |     `-- employment_contracts
  |-- pay_periods
  |     `-- pay_runs
  |          |-- payroll_run_lines
  |          |    `-- payroll_line_items
  |          `-- payroll_ledger_entries
  |-- user_tenant_roles -- users
  |
roles -- role_permissions -- permissions

idempotency_keys store safe create responses per route.
audit_logs remain append-only for operational evidence.
```

## 2. `tenants`

Employer organisations. Tenant IDs are the isolation boundary for employee,
contract and future payroll data.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `name` | `varchar(200)` | Display name |
| `legal_name` | `varchar(255)` | Registered employer name |
| `slug` | `varchar(80)` | Unique stable slug |
| `company_registration_number` | `varchar(32)` | Nullable |
| `paye_reference` | `varchar(32)` | HMRC PAYE reference |
| `accounts_office_reference` | `varchar(32)` | HMRC accounts office reference |
| `default_pay_frequency` | `varchar(20)` | `weekly`, `fortnightly`, `four_weekly`, `monthly` |
| `status` | `varchar(20)` | `active` by default |
| `created_at` / `updated_at` | `timestamptz` | Server-managed timestamps |

Seeded default tenant: `snovasys-futuristic`.

## 3. `users`

Application users: Snovasys operators, payroll officers, employer admins and
future employee self-service accounts.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `email` | `citext` | Unique, case-insensitive in Postgres |
| `full_name` | `varchar(255)` | |
| `hashed_password` | `varchar(255)` | bcrypt |
| `role` | `varchar(32)` | Coarse legacy field retained for compatibility |
| `is_active` | `boolean` | |
| `is_superuser` | `boolean` | |
| `created_at` / `updated_at` | `timestamptz` | Server-managed timestamps |

RBAC authorization now uses `user_tenant_roles` rather than relying only on the
legacy `users.role` value.

## 4. RBAC Tables

### `roles`

System roles: `tenant_owner`, `payroll_admin`, `payroll_viewer`,
`employee_self_service`.

### `permissions`

System permissions include `tenants:manage`, `rbac:manage`, `employees:read`,
`employees:write`, `contracts:manage` and `payroll:run`.

### `role_permissions`

Many-to-many mapping between roles and permissions.

### `user_tenant_roles`

Tenant-scoped role assignment.

| Column | Type | Notes |
|---|---|---|
| `user_id` | `uuid` | FK to users |
| `tenant_id` | `uuid` | FK to tenants |
| `role_id` | `uuid` | FK to roles |
| `is_active` | `boolean` | Supports deactivation without deletion |

## 5. `employees`

The payroll record for a person paid by an employer.

| Column | Type | Notes |
|---|---|---|
| `id` | `uuid` | Primary key |
| `tenant_id` | `uuid` | FK to tenants, required |
| `employee_number` | `varchar(40)` | Unique per tenant |
| `first_name` / `last_name` | `varchar` | Employee identity |
| `email` | `citext` / `varchar(255)` | Unique per tenant |
| `national_insurance_number` | `varchar(9)` | Unique per tenant |
| `tax_code` | `varchar(10)` | Default `1257L` |
| `ni_category` | `varchar(1)` | Default `A` |
| `employment_start_date` | `date` | Required |
| `employment_status` | `varchar(20)` | Default `active` |
| `job_title` | `varchar(150)` | Nullable |
| `created_at` / `updated_at` | `timestamptz` | Server-managed timestamps |

Validation at the schema layer:

- NI number matches `^[A-CEGHJ-PR-TW-Z]{2}\d{6}[A-D]$`.
- Tax code matches common UK patterns: `1257L`, `BR`, `D0`, `D1`, `NT`,
  K-codes and numeric suffix codes.
- NI category is one of the supported HMRC category codes exposed by
  `/api/v1/framework`.

## 6. `employment_contracts`

Contracts are the bridge from employee records into payroll calculation.

| Column | Type | Notes |
|---|---|---|
| `tenant_id` | `uuid` | FK to tenants |
| `employee_id` | `uuid` | FK to employees |
| `contract_type` | `varchar(32)` | `permanent`, `fixed_term`, `apprentice`, `casual` |
| `pay_frequency` | `varchar(20)` | Weekly/monthly framework code |
| `annual_salary` | `numeric(14,2)` | Nullable for hourly/casual arrangements |
| `weekly_hours` | `numeric(5,2)` | Nullable |
| `effective_from` / `effective_to` | `date` | Contract date range |
| `currency` | `varchar(3)` | `GBP` by default |
| `is_primary` | `boolean` | Primary contract flag |

Unique constraint: one contract per employee per `effective_from` date.

## 7. `idempotency_keys`

Stores create responses by `(key, method, path)` to make retries safe.
Create endpoints reserve this row before writing the target resource and update
the stored response before committing, so concurrent same-key retries replay
the original response instead of racing the resource uniqueness checks.

| Column | Type | Notes |
|---|---|---|
| `key` | `varchar(128)` | Client-supplied `Idempotency-Key` |
| `method` / `path` | `varchar` | Route identity |
| `request_hash` | `varchar(64)` | SHA-256 over method, path and payload |
| `status_code` | `integer` | Original status |
| `response_body` | `json/jsonb` | Original response |
| `tenant_id` | `uuid` | Nullable tenant context |
| `created_at` / `expires_at` | `timestamptz` | Expiry is reserved for retention cleanup |

Reusing the same key with a different payload returns `409 Conflict`.

## 8. Row-Level Security

Migration `20260501_0002` enables Postgres RLS policies for:

- `tenants`
- `employees`
- `employment_contracts`
- `user_tenant_roles`
- `idempotency_keys`

Tenant-scoped policies use `current_setting('app.tenant_id', true)` as the
runtime tenant context. Auth dependencies set the tenant and superuser database
settings before tenant-scoped ORM work runs.

## 9. Milestone 3 Payroll Engine

### `pay_periods`

Tenant payroll cycles by tax year, pay frequency and period number.

### `pay_runs`

Calculated payroll run aggregate for a pay period.

| Column | Type | Notes |
|---|---|---|
| `tenant_id` | `uuid` | Tenant isolation boundary |
| `pay_period_id` | `uuid` | FK to `pay_periods` |
| `status` | `varchar(20)` | `calculated` in M3 |
| `employee_count` | `integer` | Number of calculated employee lines |
| `gross_earnings` | `numeric(14,2)` | Base salary plus manual earnings |
| `total_deductions` | `numeric(14,2)` | Manual deductions |
| `net_pay` | `numeric(14,2)` | Gross less deductions |
| `ledger_entry_hash` | `varchar(64)` | Hash of the latest ledger entry for this run |

### `payroll_run_lines`

Employee-level calculation results for a pay run. M3 stores base salary,
additional earnings, deductions and net pay. PAYE and NI fields arrive in M4-M5.

### `payroll_line_items`

Evidence rows for base salary, manual earnings and manual deductions.

### `payroll_ledger_entries`

Append-only hash-chain evidence for calculated pay runs. Each entry stores a
canonical payload hash, previous hash and entry hash. The M3 Postgres migration
adds a trigger that rejects updates and deletes against ledger entries.

## 10. Upcoming Entities

- `payslips`
- `tax_code_history`
- `ni_reference_data`
- `statutory_payments`
- `pension_schemes`
- `rti_submissions`
- `hmrc_credentials`

All monetary columns will use `NUMERIC(14,2)`. Rate columns will use fixed
precision decimal types; float arithmetic is not allowed for payroll money.

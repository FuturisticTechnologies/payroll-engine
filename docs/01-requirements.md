# 01 - Requirements

## 1. Objective

Design, build and deploy a UK-compliant payroll SaaS that aligns with HMRC
regulations, statutory requirements and enterprise-grade operational standards.
The platform must be robust, scalable, secure and compliant with UK payroll
legislation.

## 2. Scope of Work

### 2.1 Core Payroll Capabilities

| Capability | Description |
|---|---|
| Employee payroll processing | Monthly, weekly, fortnightly and four-weekly pay cycles |
| PAYE calculations | Income tax per HMRC tax tables and tax codes |
| National Insurance | NI categories, Class 1 primary/secondary and director rules |
| Pension auto-enrolment | UK-compliant schemes such as NEST and People's Pension |
| Statutory payments | SSP, SMP and SPP eligibility and payment calculations |
| Tax codes and allowances | 1257L, BR, D0, D1, NT, K-codes and emergency codes |
| Payslip generation | Digital payslips and downloadable PDF |
| Deductions and adjustments | Pre-tax, post-tax, loans, advances and court orders |

### 2.2 HMRC Compliance and Integrations

| Area | Deliverable |
|---|---|
| RTI FPS | Full Payment Submission per pay run |
| RTI EPS | Employer Payment Summary per period |
| HMRC API integration | OAuth2 client, FPS/EPS submit and error reconciliation |
| Year-end processing | P60 generation for active employees |
| Leaver processing | P45 issuance |
| Legislation updates | Annual tax table refresh pipeline |

### 2.3 System and Platform Features

- Employer tenants with tenant-scoped employee and payroll data.
- Role-based access control for Snovasys operators, tenant owners, payroll admins, viewers and employee self-service users.
- Audit logs for every data-mutating action.
- Reporting and analytics for payroll summaries, liabilities and year-to-date views.
- Integration capability with external HRMS and accounting platforms.
- Data security aligned with UK GDPR and OWASP ASVS L2.

## 3. Non-Functional Requirements

| Category | Target |
|---|---|
| Availability | >= 99.9% monthly in production |
| RTO / RPO | 1 hour / 15 minutes |
| Concurrency | 10k concurrent employer sessions at steady state |
| Payslip batch | 50k payslips per hour per tenant |
| API latency | p95 < 300 ms for reads, p95 < 800 ms for writes |
| Security | OWASP ASVS L2, UK GDPR and ISO 27001-aligned controls |
| Observability | Structured JSON logs, traces, metrics and alerting |
| Auditability | Immutable append-only audit log with 7-year retention |
| Localisation | English (UK), GBP, UK date/time and UK tax-year boundaries |

## 4. Users and Roles

| Role | Description | Milestone 2 scope |
|---|---|---|
| Super admin | Snovasys operator | Seeded local admin and tenant-owner assignment |
| Tenant owner | Employer administrator | RBAC role and tenant mapping |
| Payroll admin | Runs payroll operations | RBAC role and employee/contract permissions |
| Payroll viewer | Read-only payroll stakeholder | RBAC role and read permission |
| Employee self-service | Views own payslips and profile | RBAC role placeholder, portal in M10 |

## 5. Delivered in Milestone 1

- Requirements, architecture, data model, security/GDPR, HMRC, API and deployment docs.
- Runnable scaffold: FastAPI, PostgreSQL, Angular and Docker Compose.
- Initial Alembic schema for users, employees and audit logs.
- Health, readiness, meta, auth-login and employee scaffold endpoints.
- Backend and frontend CI workflow foundations.

## 6. Delivered in Milestone 2

- Employer tenant model and default Snovasys/Futuristic tenant seed.
- RBAC models and bearer-token permission enforcement for M2 routes.
- Tenant-scoped employee structure with employee number, NI category and employment status.
- Employment contract model for pay frequency, contract type, salary, hours and effective dates.
- Payroll framework catalog for pay frequencies, contract types, NI categories, roles and permissions.
- Transactional create endpoint idempotency using `Idempotency-Key`.
- Security hardening: CSP, frame protection, content sniffing protection, production HSTS and CSRF bootstrap/guard.
- Strict Postgres row-level security policies for tenant-scoped tables.
- Angular dashboard and payroll framework view for M2 operational visibility.

## 7. Out of Scope for Milestone 2

- PAYE and National Insurance calculation engine, which starts in M3-M5.
- HMRC RTI submissions, which land in M6-M7.
- Statutory payment engines, which land in M8.
- Pension auto-enrolment integrations, which land in M9.
- Payslip rendering, reporting dashboards and audit UI, which land in M10.
- Enterprise SSO/MFA, which land in M9.

## 8. Acceptance Criteria for Milestone 2

1. `alembic upgrade head` creates M2 tables and applies tenant-scoped employee changes.
2. `GET /api/v1/meta/milestone` reports milestone `2` with status `complete`.
3. `GET /api/v1/tenants` returns the seeded default tenant.
4. `GET /api/v1/framework` returns pay frequencies, contract types, NI categories, roles and permissions.
5. `POST /api/v1/employees` works with M1 payloads and adds tenant ID plus employee number.
6. `POST /api/v1/employment-contracts` persists a contract for an employee.
7. Repeating a create request with the same `Idempotency-Key` returns the original response.
8. Protected M2 endpoints require a bearer token with the required RBAC permission.
9. Security headers are present on API responses.
10. Backend tests and frontend production build pass.

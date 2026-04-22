# 01 — Requirements

## 1. Objective

Design, build and deploy a UK-compliant payroll SaaS that aligns with HMRC
regulations, statutory requirements and enterprise-grade operational standards.
The platform must be robust, scalable, secure and compliant with UK payroll
legislation.

## 2. Scope of work

### 2.1 Core payroll capabilities

| Capability | Description |
|---|---|
| Employee payroll processing | Monthly and weekly pay cycles |
| PAYE calculations | Income tax per HMRC tax tables and tax codes |
| National Insurance | NI categories A–X, Class 1 primary/secondary |
| Pension auto-enrolment | UK-compliant schemes (NEST, People's Pension, etc.) |
| Statutory payments | SSP (Sick), SMP (Maternity), SPP (Paternity) |
| Tax codes & allowances | 1257L, BR, D0, D1, NT, K-codes, emergency codes |
| Payslip generation | Digital payslips, downloadable PDF |
| Deductions & adjustments | Pre-tax and post-tax, loans, advances, court orders |

### 2.2 HMRC compliance & integrations

| Area | Deliverable |
|---|---|
| RTI FPS | Full Payment Submission, per pay run |
| RTI EPS | Employer Payment Summary, monthly/period |
| HMRC API integration | OAuth2 client, FPS/EPS submit, error reconciliation |
| Year-end processing | P60 generation for active employees |
| Leaver processing | P45 issuance |
| Legislation updates | Annual tax table refresh pipeline |

### 2.3 System & platform features

- Role-based access control (admin, payroll officer, employer, employee)
- Audit logs for every data-mutating action
- Reporting and analytics: payroll summaries, liability reports, YTD
- Integration capability with external HRMS and accounting platforms
- Data security aligned with UK GDPR

### 2.4 Engineering & delivery

- Frontend and backend development
- API-first architecture
- Data pipelines and reporting structures
- Automated testing and QA
- CI/CD pipelines and deployment automation
- Production deployment and stabilisation

## 3. Non-functional requirements

| Category | Target |
|---|---|
| Availability | ≥ 99.9% monthly (production) |
| RTO / RPO | 1 hour / 15 minutes |
| Concurrency | 10k concurrent employer sessions at steady state |
| Payslip batch | 50k payslips per hour per tenant |
| API latency | p95 < 300 ms for reads, < 800 ms for writes |
| Security | OWASP ASVS L2; UK GDPR; ISO 27001-aligned controls |
| Observability | Structured JSON logs, traces, metrics, alerting |
| Auditability | Immutable append-only audit log, 7-year retention |
| Localisation | English (UK), GBP, UK date/time, UK tax year boundaries |

## 4. Users and roles

| Role | Description | Milestone 1 scope |
|---|---|---|
| Super admin | Snovasys operator | User management stub |
| Employer admin | Tenant owner | Read-only dashboard stub |
| Payroll officer | Runs pay cycles | Schema in place, actions in M3 |
| Employee (self-service) | Views own payslips | Model present, portal in M10 |

## 5. In scope for Milestone 1

- [x] Requirement document (this file)
- [x] Architecture design ([02-architecture.md](./02-architecture.md))
- [x] Data model baseline ([03-data-model.md](./03-data-model.md))
- [x] Security & UK GDPR posture ([04-security-gdpr.md](./04-security-gdpr.md))
- [x] HMRC compliance outline ([05-hmrc-compliance.md](./05-hmrc-compliance.md))
- [x] API design conventions ([06-api-design.md](./06-api-design.md))
- [x] Deployment plan ([07-deployment.md](./07-deployment.md))
- [x] Runnable skeleton: FastAPI + PostgreSQL + Angular + Docker Compose
- [x] Initial schema migration
- [x] Health, meta, and employee scaffold endpoints
- [x] CI pipelines for backend and frontend

## 6. Out of scope for Milestone 1

- PAYE / NI calculation engine (Milestone 3–5)
- HMRC RTI submissions (Milestone 6–7)
- Statutory payment engines (Milestone 8)
- Pension auto-enrolment integrations (Milestone 9)
- Payslip rendering, dashboards, audit UI (Milestone 10)
- Full role-based access control beyond a single `role` field
- Multi-tenant isolation (row-level security is planned for Milestone 2)

## 7. Acceptance criteria for Milestone 1

1. `docker compose up --build` brings up Postgres, Redis, backend and frontend.
2. `GET /api/v1/health` returns `200 OK` with version and environment.
3. `GET /api/v1/health/ready` returns `200 OK` after Postgres is reachable.
4. `POST /api/v1/employees` persists a row with NI number and tax code validation.
5. `alembic upgrade head` creates `users`, `employees`, `audit_logs` tables.
6. Backend test suite passes (`pytest`).
7. Frontend dashboard renders and reads from the backend.
8. CI pipelines (backend + frontend) pass on push.
9. All documents in `docs/` are present and reviewed.

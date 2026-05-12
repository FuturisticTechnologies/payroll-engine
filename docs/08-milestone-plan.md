# 08 - Milestone Plan

Aligned with Section 11.8 of the SOW. 13 milestones at GBP 21,000 per
milestone, total GBP 273,000 plus applicable taxes. Project span:
10 Apr 2026 - 9 Mar 2027.

| # | Window | Theme | Key deliverables | Status |
|---|---|---|---|---|
| M1 | 10 - 30 Apr 2026 | Project initiation, requirements, architecture | Requirements, architecture, security/GDPR, HMRC outline, API design, deployment plan, runnable FastAPI + Angular + Postgres + Docker Compose scaffold, CI pipelines | Delivered |
| **M2** | **May 2026** | **Core data models, employee structures, payroll framework setup** | **Tenants, RBAC tables, row-level security, tenant-scoped employees, employment contracts, pay frequencies, idempotency, CSRF/CSP/HSTS hardening** | **Delivered** |
| M3 | Jun 2026 | Basic payroll engine | Earnings and deductions calculation, pay run aggregation, immutable ledger | Planned |
| M4 | Jul 2026 | PAYE tax calculations, tax codes, allowances | PAYE engine, tax code state machine, cumulative/non-cumulative, K-codes | Planned |
| M5 | Aug 2026 | National Insurance calculations and compliance rules | NI categories, Class 1 primary/secondary, director's NI, annual reference data | Planned |
| M6 | Sep 2026 | HMRC RTI integration, FPS submissions | HMRC OAuth client, FPS envelope builder, transmission, audit trail | Planned |
| M7 | Oct 2026 | HMRC RTI, EPS, error handling, reconciliation | EPS submissions, error state machine, retry and reconciliation UI | Planned |
| M8 | Nov 2026 | Statutory payments | SSP, SMP, SPP eligibility and payment calculation | Planned |
| M9 | Dec 2026 | Pension auto-enrolment integration | Auto-enrolment assessment, contribution calculation, adapter layer | Planned |
| M10 | Jan 2027 | Payslips, reporting, dashboards, audit logs | Payslip PDF rendering, dashboards, audit UI, self-service portal | Planned |
| M11 | Feb 2027 early | QA, automation, regression completion | E2E test suite, pen test, accessibility audit | Planned |
| M12 | Feb 2027 late | DevOps, CI/CD, deployment environments | Blue/green, metrics, tracing, alerting, disaster recovery drill | Planned |
| M13 | 1 - 9 Mar 2027 | UAT, compliance validation, production go-live | UAT sign-off, HMRC live credentials, go-live runbook | Planned |

## Gating Rules

1. A milestone is considered delivered only when its acceptance criteria are
   met and signed off.
2. No milestone starts before the previous one has merged to `main`.
3. HMRC live submissions are disabled in every environment except production
   with explicit runtime configuration.

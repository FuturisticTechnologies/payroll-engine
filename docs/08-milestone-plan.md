# 08 — Milestone plan

Aligned with Section 11.8 of the SOW. 13 milestones, £21,000 per milestone,
total £273,000 + applicable taxes. Project span: 10 Apr 2026 – 9 Mar 2027.

| # | Window | Theme | Key deliverables |
|---|---|---|---|
| **M1** | 10 – 30 Apr 2026 | **Project initiation, requirement finalisation, architecture design** | This repository — requirement doc, architecture doc, data model baseline, security/GDPR posture, HMRC compliance outline, API design, deployment plan, runnable scaffold (FastAPI + Angular + Postgres + Docker Compose), CI pipelines |
| M2 | May 2026 | Core data models, employee structures, payroll framework setup | Tenants, RBAC tables, row-level security, employment contracts, pay frequencies, idempotency, CSRF/CSP/HSTS hardening |
| M3 | Jun 2026 | Basic payroll engine | Earnings and deductions calculation, pay run aggregation, immutable ledger |
| M4 | Jul 2026 | PAYE tax calculations, tax codes, allowances | PAYE engine, tax code state machine, cumulative/non-cumulative, K-codes |
| M5 | Aug 2026 | National Insurance calculations and compliance rules | NI categories A–X, Class 1 primary/secondary, director's NI, annual reference data |
| M6 | Sep 2026 | HMRC RTI integration (FPS submissions) | HMRC OAuth client, FPS envelope builder, transmission, audit trail |
| M7 | Oct 2026 | HMRC RTI (EPS), error handling, reconciliation flows | EPS submissions, error state machine, retry and reconciliation UI |
| M8 | Nov 2026 | Statutory payments (SSP, SMP, SPP) | Eligibility engine, payment calculation, interaction with PAYE |
| M9 | Dec 2026 | Pension auto-enrolment integration (NEST & others) | Auto-enrolment assessment, contribution calc, adapter layer |
| M10 | Jan 2027 | Payslips, reporting, dashboards, audit logs | Payslip rendering (PDF), dashboards, audit UI, self-service portal |
| M11 | Feb 2027 (Early) | QA, automation, regression testing completion | End-to-end test suite, pen test, accessibility audit |
| M12 | Feb 2027 (Late) | DevOps, CI/CD pipelines, deployment environments | Blue/green, metrics, tracing, alerting, DR drill |
| M13 | 1 – 9 Mar 2027 | UAT, compliance validation, production go-live | UAT sign-off, HMRC live credentials, go-live runbook |

## Gating rules

1. A milestone is considered delivered only when acceptance criteria in
   its milestone README are met and signed off.
2. No milestone starts before the previous one has merged to `main`.
3. HMRC live submissions are disabled in every environment except
   **production** with explicit runtime configuration.

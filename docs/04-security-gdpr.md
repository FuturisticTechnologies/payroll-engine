# 04 - Security & UK GDPR

## 1. Threat Model Summary

| Asset | Threats | Mitigation |
|---|---|---|
| Employee PII | Disclosure, exfiltration | TLS, RBAC, RLS, audit trail and future field encryption |
| Payroll figures | Tampering | Immutable audit trail and signed pay-run ledger in later milestones |
| HMRC credentials | Theft | Vault/KMS and per-tenant isolation in M6-M7 |
| Session tokens | Hijack | Short TTL JWTs, production CSRF guard and future HttpOnly refresh cookies |
| Application containers | Compromise | Non-root images, pinned dependencies and CI scanning |
| Database | Unauthorised access | Private networking, strong secrets, tenant RLS policies |

## 2. Delivered Controls

### 2.1 Network and Transport

- TLS is required for public production endpoints.
- Production responses include HSTS: `max-age=31536000; includeSubDomains`.
- API responses include `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `Cross-Origin-Opener-Policy` and `Permissions-Policy`.

### 2.2 Authentication and Authorisation

- `/api/v1/auth/login` returns JWT access and refresh tokens.
- RBAC tables are present and enforced on tenant, employee, contract and
  framework endpoints.
- Development admin is seeded as tenant owner for the default tenant.
- Bearer tokens carry tenant and permission claims; the API validates them
  against persisted user-tenant role assignments.

### 2.3 Tenant Isolation

- `tenants` is the employer boundary.
- `employees`, `employment_contracts`, `user_tenant_roles` and
  `idempotency_keys` carry tenant context.
- Postgres RLS policies are created by migration `20260501_0002`, forced on
  tenant tables and use request-scoped `app.tenant_id` plus `app.is_superuser`
  database settings.

### 2.4 Application-Layer Controls

- Pydantic validates all request payloads.
- Angular interpolation provides safe output encoding by default.
- CSP is returned on API responses.
- `/api/v1/auth/csrf` issues a double-submit token. Production unsafe
  cookie-based writes require a matching `csrf_token` cookie and
  `X-CSRF-Token` header unless the request uses bearer authentication.
- Idempotency reserves create requests before resource writes and completes the
  replay record in the same transaction, including concurrent retry protection.
- M3 payroll ledger entries are append-only in the API and protected by a
  Postgres trigger that rejects updates and deletes.

### 2.5 Secrets

- No secrets should be committed.
- `.env.example` and `backend/.env.example` contain placeholder or development
  values only.
- Production secrets should come from a vault or cloud secret manager.

## 3. UK GDPR Posture

PayrollFuturistic processes personal data on behalf of employers. Employers
are controllers; Snovasys acts as processor under UK GDPR.

| Right | Implementation target |
|---|---|
| Right of access | Employee self-service export in M10 |
| Right to rectification | Employee profile edit plus audit trail |
| Right to erasure | Controller-led workflow subject to HMRC retention |
| Right to data portability | JSON/CSV export in M10 |
| Right to object | Usually not applicable to statutory payroll processing |

Retention:

- Payroll records: 6 years after the end of the tax year.
- Audit records: 7 years.
- Authentication logs: 12 months hot, 36 months cold.

Data residency target: UK region or equivalent customer-approved hosting.

## 4. Security Milestones

| Milestone | Security deliverable |
|---|---|
| M1 | Baseline controls, container runtime, dependency pinning and structured logs |
| M2 | RBAC tables, RLS policies, CSP, HSTS, CSRF guard and idempotency |
| M3 | Payroll run ledger integrity and tenant-scoped pay-run RLS |
| M4-M5 | SAST gates, secrets scanning and image scanning |
| M6-M7 | HMRC OAuth credentials in Vault and encrypted RTI envelopes |
| M9 | SSO/OIDC and MFA for privileged roles |
| M11 | Penetration test and remediation |
| M12 | Threat model review and disaster recovery exercise |

# 04 — Security & UK GDPR

## 1. Threat model (summary)

| Asset | Threats | Mitigation |
|---|---|---|
| Employee PII (name, NI, bank) | Disclosure, exfiltration | Encryption in transit + at rest, RBAC, RLS, audit log |
| Payroll figures | Tampering | Immutable audit trail, signed pay runs |
| HMRC credentials | Theft | Vault/KMS, short-lived tokens, per-tenant isolation |
| Session tokens | Hijack | HttpOnly cookies (M2), short TTL, rotation, TLS only |
| Application containers | Compromise | Least-privilege, non-root, SBOM + image scanning |
| Database | Unauthorised access | Private networking, IAM, strong secret rotation |

## 2. Controls

### 2.1 Network and transport

- TLS 1.2+ on all public endpoints. HTTP redirected to HTTPS at the edge.
- HSTS (`max-age=31536000; includeSubDomains`) from M2.
- Internal traffic between application and database inside a private VPC.

### 2.2 Authentication and authorisation

- OAuth2 password flow for first-party login, JWT access tokens
  (15–30 min TTL), opaque refresh tokens in HttpOnly cookies from M2.
- SSO (OIDC) support from M9 for enterprise customers.
- MFA for admin roles from M9.
- RBAC with a hierarchical role model (`super_admin`, `tenant_admin`,
  `payroll_officer`, `employer_manager`, `employee_self_service`).
- Row-level security in Postgres: every table carries `tenant_id`, and
  RLS policies filter by the current tenant context (M2).

### 2.3 Data protection

- Encryption in transit (TLS) is mandatory.
- Encryption at rest via the disk layer for Postgres and object storage.
- Field-level encryption for highly sensitive fields (bank account, NI
  number storage) is under evaluation for M4 — encrypted with a per-tenant
  data encryption key wrapped by a KMS master key.
- Data minimisation: no PII stored that is not required to run payroll.

### 2.4 Secrets

- No secrets in the repo. `.env.example` ships placeholder values only.
- Production secrets come from Vault / cloud KMS, injected at runtime.
- Rotation policy: 90-day rotation for service credentials, 12-month for
  signing keys, immediate rotation on compromise.

### 2.5 Application-layer controls

- Input validation via Pydantic at every edge.
- Output encoding / templating safe by default (Angular interpolation).
- CSRF protection for cookie-based sessions (M2).
- Strict `Content-Security-Policy` header (M2).
- Rate limiting per route, per actor (via Redis).
- Dependency pinning + weekly SCA (pip-audit, npm audit) in CI.
- Static analysis: ruff + mypy (backend), ESLint (frontend), SAST (M2).

### 2.6 Auditability

- Every data-mutating action is emitted as an append-only audit record.
- Audit records carry: actor, source IP, event type, entity type/id,
  JSON payload, timestamp. See [`03-data-model.md`](./03-data-model.md).
- 7-year retention to support HMRC investigations.

## 3. UK GDPR posture

PayrollFuturistic processes personal data on behalf of employers
(data controllers). Snovasys acts as a **processor** under UK GDPR.

### 3.1 Lawful basis

- Processing is performed under the **contractual necessity** basis
  between the employer and Snovasys (Article 6(1)(b) UK GDPR).
- Special category data is not stored beyond what HMRC requires.

### 3.2 Data subject rights

| Right | Implementation (target milestone) |
|---|---|
| Right of access | Self-service export in employee portal (M10) |
| Right to rectification | Employee profile edit (M2) + audit trail |
| Right to erasure | Controller-initiated, subject to HMRC retention (M12) |
| Right to data portability | JSON + CSV export (M10) |
| Right to object | Not generally applicable to statutory payroll processing |

### 3.3 Retention

- Payroll records: 6 years after the end of the tax year (HMRC).
- Audit records: 7 years.
- Authentication logs: 12 months hot, 36 months cold.

### 3.4 Data residency

- UK (eu-west-2 or equivalent). No cross-border transfer without SCCs.

### 3.5 Sub-processors

- The list of sub-processors (cloud provider, email provider, error
  reporting) is maintained in the customer trust centre from M11.

## 4. Security milestones

| Milestone | Security deliverable |
|---|---|
| M1 (this) | Baseline controls document; containerised runtime; dependency pinning; non-root images; structured logs |
| M2 | RBAC tables, RLS enabled, CSRF, CSP, HSTS, audit log writes |
| M3–M5 | SAST gates in CI, secrets scanning, image scanning |
| M6–M7 | HMRC OAuth credentials in Vault; encrypted RTI envelopes |
| M9 | SSO (OIDC) + MFA for privileged roles |
| M11 | Penetration test + remediation |
| M12 | Threat model review; DR exercise |

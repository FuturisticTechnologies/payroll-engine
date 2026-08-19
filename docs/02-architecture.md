# 02 - Architecture

## 1. Guiding Principles

1. API-first. Every capability is exposed as a versioned REST resource.
2. Strict types end to end. Pydantic validates the edge, SQLAlchemy maps
   persistence and TypeScript types the UI.
3. Async by default. FastAPI uses async SQLAlchemy sessions for runtime I/O.
4. Immutable audit posture. Data mutations are designed to emit append-only
   audit events as the domain layer matures.
5. Stateless compute, stateful storage. Durable state lives in Postgres and
   future object storage.
6. Twelve-factor configuration. Environment-specific values come from env vars.
7. Compliance by construction. PII is minimised and tenant-scoped.

## 2. High-Level View

```text
Browser / Angular SPA
        |
        | HTTPS / JSON
        v
FastAPI API
        |-- routing and validation
        |-- auth and RBAC schema
        |-- tenant-aware payroll framework
        |-- basic payroll calculation engine
        |-- security headers and request IDs
        |
        v
PostgreSQL 16
        |-- tenants
        |-- employees
        |-- employment contracts
        |-- pay periods and pay runs
        |-- payroll ledger entries
        |-- RBAC tables
        |-- audit logs
        |-- row-level security policies

Redis 7 is included in the local stack for sessions, rate limiting and future
background jobs.
```

## 3. Components

### 3.1 Frontend - Angular 21

- Standalone components and router-level lazy loading.
- Signals for local component state.
- `HttpClient` wrapper in `ApiService`.
- `OnPush` change detection.
- Current pages: dashboard, employees, payroll framework, payroll runs and
  system health.

### 3.2 Backend - FastAPI

- `app/api/v1/` owns HTTP endpoint routing.
- `app/models/` owns persistence models.
- `app/schemas/` owns request and response validation.
- `app/core/` owns configuration, database, security, tenancy, idempotency and
  payroll calculation helpers.
- OpenAPI docs are generated at `/docs`, `/redoc` and `/openapi.json`.

### 3.3 Database - PostgreSQL 16

- Alembic manages versioned migrations.
- `20260410_0001` creates users, employees and audit logs.
- `20260501_0002` creates tenants, RBAC, employment contracts, idempotency keys
  and tenant row-level security policies.
- `20260601_0003` creates pay periods, payroll runs, line items and immutable
  payroll ledger entries.
- Monetary values use fixed-precision `NUMERIC`, never floats.

### 3.4 Cache and Queue - Redis 7

Redis is part of the runtime topology. M3 does not yet enforce Redis-backed
rate limiting; it remains the planned primitive for sessions, throttling and
background payroll jobs.

### 3.5 HMRC Integration Layer

HMRC integration begins in M6. The current architecture reserves the API and
data boundaries needed for per-tenant HMRC credentials, RTI submissions and
auditable request/response records.

## 4. Request Lifecycle

1. Browser calls a versioned endpoint such as `GET /api/v1/framework`.
2. FastAPI middleware binds a request ID and applies security headers.
3. The router resolves the endpoint in `app/api/v1/endpoints/`.
4. `get_db()` yields an async SQLAlchemy session.
5. The endpoint validates input, resolves tenant context when required and
   performs ORM reads/writes.
6. Create endpoints reserve an idempotency row before the resource write and
   complete it in the same transaction.
7. Pay-run creation invokes the M3 calculation engine, persists employee lines
   and appends hash-chain ledger evidence.
8. Pydantic response models serialise the result.

## 5. Deployment Topology

| Environment | Purpose | Infrastructure |
|---|---|---|
| Local | Developer inner loop | Docker Compose |
| CI | Pull-request validation | GitHub Actions with ephemeral services |
| Dev | Integration | Shared container host or Kubernetes |
| Staging | HMRC test and UAT rehearsal | Isolated production-like environment |
| Production | Live payroll service | Multi-AZ managed infrastructure |

## 6. Cross-Cutting Concerns

| Concern | Mechanism |
|---|---|
| Config | `pydantic-settings`, env-driven, validated on boot |
| Logging | `structlog` with request ID context |
| Security headers | FastAPI middleware |
| Idempotency | `idempotency_keys` table |
| Tenant isolation | `tenant_id` plus Postgres RLS |
| Payroll ledger | Append-only `payroll_ledger_entries` hash chain |
| Secrets | Vault or cloud KMS, never committed |
| Metrics | Prometheus planned in M12 |
| Tracing | OpenTelemetry planned in M12 |

## 7. Technology Justification

| Decision | Alternatives considered | Why |
|---|---|---|
| FastAPI | Django REST, Flask, .NET Core | Async, typed, strong OpenAPI experience |
| PostgreSQL | MySQL, SQL Server | Strict types, numerics, RLS, JSONB and Alembic support |
| Angular | React, Vue | Opinionated, enterprise-friendly and team-aligned |
| Redis | Memcached, Kafka | One primitive for cache, sessions and jobs |
| Docker Compose | Native installs | Repeatable local stack |

# 02 — Architecture

## 1. Guiding principles

1. **API-first.** Every capability is exposed as a versioned REST resource.
   The SPA is one client, the HMRC integration is another, partners are a
   third.
2. **Strict types end-to-end.** Pydantic on the edge, SQLAlchemy for
   persistence, TypeScript on the UI. Money is `Decimal`, never float.
3. **Async by default.** Async FastAPI + asyncpg. Background work is offloaded
   to Redis-backed workers (arq/Celery) from Milestone 2 onward.
4. **Immutable audit.** Every state change is accompanied by an append-only
   audit event. Audit rows are never updated or deleted.
5. **Stateless compute, stateful storage.** Application containers are
   horizontally scalable. All durable state lives in Postgres or object storage.
6. **Twelve-factor configuration.** All environment-specific values come
   from env vars, validated on boot.
7. **Compliance by construction.** PII is minimised, encrypted in transit and
   at rest, and protected by RBAC + row-level security (Milestone 2).

## 2. High-level view

```
                ┌──────────────────────────────┐
                │         Browser (SPA)        │
                │   Angular 18 · TypeScript    │
                └──────────────┬───────────────┘
                               │ HTTPS / JSON
                               ▼
┌────────────────────────────────────────────────────────────┐
│                      API Gateway / WAF                     │
│                (TLS termination, rate limit)               │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
             ┌──────────────────────────┐
             │   FastAPI App (uvicorn)  │
             │  • routing / validation  │
             │  • auth / RBAC           │
             │  • domain services       │
             │  • HMRC client           │
             └────┬────────────┬────────┘
                  │            │
          async / │            │ outbound
          queries │            │ HTTPS
                  ▼            ▼
        ┌──────────────┐  ┌──────────────┐
        │  PostgreSQL  │  │  HMRC APIs   │
        │  (primary)   │  │ (test/prod)  │
        └──────┬───────┘  └──────────────┘
               │
               │  logical replication (M7+)
               ▼
        ┌──────────────┐    ┌──────────────┐
        │  Read replica│    │    Redis     │
        │  (reporting) │    │ (cache/jobs) │
        └──────────────┘    └──────────────┘
```

## 3. Components

### 3.1 Frontend — Angular 18 (standalone)

- Standalone components, signals for local state.
- Router-level lazy loading (one chunk per feature module).
- `HttpClient` with a global `apiBaseUrlInterceptor`.
- `OnPush` change detection everywhere.
- Karma + Jasmine for unit tests. Playwright adopted in Milestone 11.

### 3.2 Backend — Python 3.12 + FastAPI

- ASGI via uvicorn (dev) and gunicorn + uvicorn workers (prod).
- `app/api/v1/` owns HTTP concerns.
- `app/services/` owns domain orchestration (added in M2).
- `app/models/` owns persistence.
- `app/schemas/` owns request/response validation.
- `app/core/` owns cross-cutting infra (config, logging, security, DB).

### 3.3 Database — PostgreSQL 16

- Primary storage for all payroll data.
- Schemas: `payroll` (domain), `audit` (append-only), `reference` (tax tables).
- Numeric money: `NUMERIC(14, 2)` for amounts, `NUMERIC(6, 4)` for rates.
- Row-level security enabled per tenant in Milestone 2.
- Alembic for versioned schema migrations.

### 3.4 Cache & queue — Redis 7

- Session store, rate-limit counters, idempotency keys.
- Background job broker (arq) for pay run calculation, HMRC submissions,
  payslip rendering — introduced from Milestone 3.

### 3.5 HMRC integration layer

- Dedicated `app/integrations/hmrc/` package (from Milestone 6).
- OAuth2 client credentials + per-employer delegated tokens.
- Strict request/response schemas; every interaction is audit-logged.
- Exponential backoff and circuit breaker on transport errors.

## 4. Request lifecycle (M1)

1. Browser sends `GET /api/v1/employees` to the backend.
2. FastAPI middleware applies CORS, structured logging context, request ID.
3. Router resolves the endpoint in `employees.py`.
4. `get_db()` dependency yields an `AsyncSession` from the pool.
5. Handler runs a SQLAlchemy statement against Postgres.
6. Rows are mapped via `EmployeeRead.model_validate(...)` for a typed response.
7. Response is serialised; audit log entry is queued (Milestone 2+).

## 5. Deployment topology (target)

| Environment | Purpose | Infrastructure |
|---|---|---|
| Local | Developer inner loop | Docker Compose |
| CI | PR validation | GitHub Actions + ephemeral services |
| Dev | Integration | Kubernetes (shared) or a single VM |
| Staging | Pre-prod, HMRC test API | Kubernetes, isolated namespace |
| Production | Live | Kubernetes, multi-AZ, dedicated cluster |

## 6. Cross-cutting concerns

| Concern | Mechanism |
|---|---|
| Config | `pydantic-settings`, env-driven, validated on boot |
| Logging | `structlog` JSON in staging/prod, console in dev |
| Tracing | OpenTelemetry (planned M12) |
| Metrics | Prometheus exposition (planned M12) |
| Error reporting | Sentry (planned M11) |
| Secrets | Vault or cloud KMS (never in repo) |
| Feature flags | Unleash or equivalent (planned M10) |

## 7. Technology justification

| Decision | Alternatives considered | Why |
|---|---|---|
| FastAPI | Django REST, Flask, .NET Core | Async, typed, modern, fastest OpenAPI DX |
| PostgreSQL | MySQL, SQL Server | Strict types, numerics, RLS, JSONB, mature Alembic story |
| Angular | React, Vue | Opinionated, enterprise-friendly, aligned with team skills |
| Redis | Memcached, Kafka | One tool for cache + jobs + pub/sub at our scale |
| Docker Compose (local) | Native installs | One command, mirrors prod container model |

# PayrollFuturistic

A UK-compliant, API-first Payroll SaaS platform by **Snovasys Software Solutions Ltd**.

Aligned with HMRC regulations for PAYE, National Insurance, RTI, statutory
payments, pension auto-enrolment and UK GDPR.

## Status

**Milestone 2 - Core Data Models, Employee Structures, Payroll Framework Setup**
(1 May 2026 - 31 May 2026)

Milestone 2 extends the Milestone 1 runnable scaffold with:

- Employer tenants with seeded Snovasys/Futuristic default tenant.
- Tenant-scoped employees with employee numbers, NI category and employment status.
- RBAC tables and bearer-token permission enforcement for M2 tenant, employee,
  contract and framework endpoints.
- Employment contracts with contract type, pay frequency, salary, hours and dates.
- Payroll framework catalog endpoint for pay frequencies, contract types, NI categories and roles.
- Transactional idempotency support for create endpoints through `Idempotency-Key`.
- Security headers for CSP, HSTS in production, frame protection, content sniffing
  protection and CSRF bootstrap/guard.
- Alembic migration `20260501_0002` with strict Postgres row-level security
  policies and forced tenant isolation.

See [`docs/`](./docs) for requirements, architecture, data model, HMRC compliance
notes, security/GDPR posture, API design and deployment guidance.

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Backend API | Python 3.12 + FastAPI | Async, typed, API-first, strong integration DX |
| ORM | SQLAlchemy 2.x + Alembic | Typed models and migration-driven schema |
| Frontend | Angular 21 standalone | Enterprise-grade, typed, component-driven UI |
| Database | PostgreSQL 16 | Strict types, numeric precision, RLS, JSONB audit/context |
| Cache / Jobs | Redis 7 | Session store, rate limit and background job foundation |
| Auth | OAuth2 + JWT | Standard, stateless, SSO-ready |
| Runtime | Docker Compose | One command brings up the local stack |
| CI | GitHub Actions | Backend, frontend and security pipelines |

## Quick Start

### Prerequisites

- Docker Desktop or Docker Engine + Compose v2
- Git
- Optional native development: Python 3.12, Node 20+, npm

### Run the Whole Stack

```bash
cp .env.example .env
docker compose up --build
```

Then open:

| Service | URL |
|---|---|
| Frontend | http://localhost:4200 |
| Backend API | http://localhost:8000 |
| OpenAPI docs | http://localhost:8000/docs |
| Health check | http://localhost:8000/api/v1/health |
| Postgres | localhost:5432, user `payroll` |

Development admin credentials are seeded automatically in non-production
environments after the database is available:

| Email | Password |
|---|---|
| `admin@payrollfuturistic.co.uk` | `Admin12345!` |

Stop with `Ctrl+C` and clean with:

```bash
docker compose down -v
```

### Run Only the Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

For a lightweight native run without Postgres, set SQLite URLs in `backend/.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./payrollfuturistic-dev.db
DATABASE_URL_SYNC=sqlite:///./payrollfuturistic-dev.db
```

The app creates local SQLite tables and seeds the development admin in
non-production environments.

### Run Only the Frontend

```bash
cd frontend
npm install
npm start
```

## Repository Layout

```text
PayrollFuturistic/
|-- backend/              FastAPI application, models, migrations, tests
|-- frontend/             Angular 21 standalone application
|-- docs/                 Architecture, requirements, compliance, API
|-- infra/                Database init scripts and local dev infra
|-- .github/workflows/    CI pipelines
|-- docker-compose.yml    Local orchestration
|-- Makefile              Developer shortcuts
`-- .env.example          Template environment variables
```

## Useful API Calls

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/meta/milestone
curl http://localhost:8000/api/v1/tenants
curl http://localhost:8000/api/v1/framework
```

Create endpoints accept idempotency:

```bash
curl -X POST http://localhost:8000/api/v1/employees \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-employee-001" \
  -d "{\"first_name\":\"Jane\",\"last_name\":\"Doe\",\"email\":\"jane@example.com\",\"national_insurance_number\":\"AB123456C\",\"tax_code\":\"1257L\",\"employment_start_date\":\"2026-05-01\"}"
```

## Compliance & Security

- HMRC: PAYE, NI, RTI FPS/EPS, P60, P45 and tax-code handling are tracked in
  [`docs/05-hmrc-compliance.md`](./docs/05-hmrc-compliance.md).
- UK GDPR: data minimisation, RBAC, RLS, auditability and security headers are
  tracked in [`docs/04-security-gdpr.md`](./docs/04-security-gdpr.md).
- Payroll framework: tenants, employee structure, contracts and pay frequency
  setup are tracked in [`docs/03-data-model.md`](./docs/03-data-model.md).

## License

Proprietary (c) 2026 Snovasys Software Solutions Ltd. All rights reserved.

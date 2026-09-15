# PayrollFuturistic

A UK-compliant, API-first Payroll SaaS platform by **Snovasys Software Solutions Ltd**.

Aligned with HMRC regulations for PAYE, National Insurance, RTI, statutory
payments, pension auto-enrolment and UK GDPR.

## Status

**Milestone 3 - Basic Payroll Engine**
(1 Jun 2026 - 30 Jun 2026)

Milestone 3 extends the tenant, employee and framework foundation with:

- Employer tenants with seeded Snovasys/Futuristic default tenant.
- Tenant-scoped employees with employee numbers, NI category and employment status.
- RBAC tables and bearer-token permission enforcement for M2 tenant, employee,
  contract and framework endpoints.
- Employment contracts with contract type, pay frequency, salary, hours and dates.
- Payroll framework catalog endpoint for pay frequencies, contract types, NI categories and roles.
- Transactional idempotency support for create endpoints through `Idempotency-Key`.
- Pay periods and calculated pay runs for weekly, fortnightly, four-weekly and
  monthly payroll cycles.
- Basic payroll engine for contract salary, manual earnings, manual deductions,
  gross pay, total deductions and net pay.
- Employee-level payroll run lines, line items and immutable hash-chain ledger
  evidence for each calculated run.
- Security headers for CSP, HSTS in production, frame protection, content sniffing
  protection and CSRF bootstrap/guard.
- Alembic migration `20260501_0002` with strict Postgres row-level security
  policies and forced tenant isolation, plus migration `20260601_0003` for M3
  payroll tables and append-only ledger protection.

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

## Local Setup

Windows commands below are for **PowerShell**; the bash versions are for
macOS/Linux (Git Bash on Windows also runs the `git`, `docker`, `npm` and
`curl` commands as written).

### 1. Prerequisites

| Tool | Version | Used for |
|---|---|---|
| Git | any 2.x | Cloning the repository; the pre-commit migration check calls `git` |
| Docker Desktop (or Docker Engine) with Compose v2 | Compose v2 (`docker compose`) | Recommended way to run the stack. Images: `postgres:16-alpine`, `redis:7-alpine`, `python:3.12-slim` (backend), `node:24-alpine` (frontend) |
| Python | 3.12 | Native backend, tests, linters and Alembic. `requires-python = ">=3.12"`; CI and the backend image use 3.12. 3.13+ does not work: the pinned `asyncpg==0.29.0` and `psycopg2-binary==2.9.9` publish no wheels for it |
| Node.js | 20.19+, 22.12+ or 24+ | Native frontend. Angular 21.2 requires `^20.19.0 \|\| ^22.12.0 \|\| >=24.0.0`; CI uses Node 20, the frontend image Node 24 |
| npm | bundled with Node | `npm ci` against `frontend/package-lock.json` |
| PostgreSQL | 16 (optional) | Only to run the backend natively against Postgres without Docker; SQLite is the no-install alternative |
| Redis | 7 (optional) | Started by Docker Compose; not needed natively - no M3 code reads `REDIS_URL` yet |
| Google Chrome | current (optional) | Headless browser for the Karma unit tests |
| pre-commit | any (optional) | Runs the same ruff and applied-migration checks as CI before each commit |
| GNU Make | any (optional) | `Makefile` shortcuts that wrap `docker compose`; not installed on Windows by default |

### 2. Get the Code

```bash
git clone https://github.com/FuturisticTechnologies/payroll-engine.git
cd payroll-engine
git checkout development
```

`development` is the integration branch for day-to-day work: branch from it and
merge back into it. `main` holds the released Milestone 3 code.

### 3. Configure

There are two environment templates:

| Template | Copy to | Read by | Database host |
|---|---|---|---|
| `.env.example` | `.env` | Docker Compose (variable substitution) | `postgres` (the Compose service) |
| `backend/.env.example` | `backend/.env` | The backend run natively (`uvicorn`, `alembic`) | `localhost` |

```powershell
# Windows (PowerShell), from the repository root
Copy-Item .env.example .env
Copy-Item backend\.env.example backend\.env
```

```bash
# macOS / Linux
cp .env.example .env
cp backend/.env.example backend/.env
```

The committed development defaults work as they are. The values that matter:

- `APP_SECRET_KEY` signs JWTs and must be at least 32 characters. Any local
  value is fine; `APP_ENV=production` refuses one that starts with `change-me`.
- `LOCAL_ADMIN_EMAIL` / `LOCAL_ADMIN_PASSWORD` are the development admin seeded
  on startup (password at least 8 characters).
- `DATABASE_URL` (async driver) and `DATABASE_URL_SYNC` (sync driver, used by
  Alembic) must point at the same database.
- `APP_CORS_ORIGINS` must include the origin the frontend is served from.
- `POSTGRES_PORT`, `REDIS_PORT`, `BACKEND_PORT` and `FRONTEND_PORT` are the host
  ports Compose publishes.
- `HMRC_CLIENT_ID` / `HMRC_CLIENT_SECRET` stay empty; nothing in M3 calls HMRC.

The backend reads `.env` from the current directory, so run `uvicorn`, `alembic`
and `pytest` from `backend/`. Every variable in `docker-compose.yml` has the same
default, so Compose also starts without a root `.env`.

### 4. Run Locally

#### Option A - Docker Compose (recommended)

```bash
docker compose up --build
```

On first start this:

1. creates the `pgdata` volume and runs `infra/postgres/init.sql` (extensions
   `pgcrypto` and `citext`; schemas `payroll`, `audit`, `reference`);
2. waits for the Postgres and Redis health checks, then runs
   `alembic upgrade head` and `uvicorn --reload` in the backend container;
3. seeds the development tenant, roles and admin user as the backend starts;
4. serves the Angular dev server (`npm run start:docker`) on port 4200.

`backend/` and `frontend/` are bind-mounted, so code changes reload without a
rebuild. Run `docker compose up --build -d` to start in the background and
`docker compose logs -f backend` to follow one service (`make up`, `make logs`
and `make ps` do the same with GNU Make).

#### Option B - Native backend and frontend

Backend, Windows (PowerShell):

```powershell
cd backend
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Backend, macOS / Linux:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Prepare a database ([section 5](#5-database): SQLite, or `alembic upgrade head`
against Postgres), then start the API on http://127.0.0.1:8000:

```bash
uvicorn app.main:app --reload
```

Frontend, in a second terminal:

```bash
cd frontend
npm ci
npm start
```

`npm start` runs `ng serve` on http://localhost:4200. The development build
calls the API at `http://127.0.0.1:8000/api/v1`
(`src/environments/environment.development.ts`), so keep the backend on port 8000.

You can also mix the two: `docker compose up postgres` for the database only,
then the backend natively with `backend/.env` as copied.

### 5. Database

Alembic owns the Postgres schema. Revisions live in
`backend/app/db/migrations/versions/`: `20260410_0001` (initial schema),
`20260501_0002` (M2 tenancy, RBAC and row-level security) and `20260601_0003`
(M3 payroll engine and append-only ledger).

**Docker Compose** applies them on every backend start. To run them by hand:

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

**Native PostgreSQL 16.** Create a role and database that match `backend/.env`,
then migrate (from the repository root):

```bash
psql -U postgres -c "CREATE ROLE payroll WITH LOGIN PASSWORD 'payroll_dev_pwd';"
psql -U postgres -c "CREATE DATABASE payroll OWNER payroll;"
psql -U payroll -d payroll -f infra/postgres/init.sql
cd backend
alembic upgrade head
```

The role does not need to be a superuser. The tables use forced row-level
security, and the startup seed sets the default tenant's context
(`app.tenant_id`) while it writes, so an ordinary owner role works. If the seed
fails anyway the backend logs `database.seed_failed` at ERROR with the cause.

**SQLite (no database server).** For a quick native run, replace the two
database URLs in `backend/.env`:

```env
DATABASE_URL=sqlite+aiosqlite:///./payrollfuturistic-dev.db
DATABASE_URL_SYNC=sqlite:///./payrollfuturistic-dev.db
```

Do not run `alembic upgrade head` against SQLite - the revisions are
PostgreSQL-only and stop at `CREATE EXTENSION`. The backend creates the tables
from the models on startup instead. Row-level security is not enforced on
SQLite, so use Postgres for anything tenant-isolation related. The file
`backend/payrollfuturistic-dev.db` is gitignored; delete it to start over,
because existing tables are not altered when the models change.

**Seed data.** There are no seed scripts. On every startup with an `APP_ENV`
other than `production`, `init_local_database()` in
`backend/app/core/database.py` idempotently creates:

- the default tenant `Snovasys Futuristic Technologies`
  (`00000000-0000-4000-8000-000000000001`);
- the system roles and permissions;
- the admin user from `LOCAL_ADMIN_EMAIL` / `LOCAL_ADMIN_PASSWORD`, as super
  admin and tenant owner.

If the database is unreachable at startup the seed is skipped without an error;
restart the backend once the database is up.

**New migrations** are append-only:

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
```

`scripts/check-migrations.sh`, run by the `no-edited-migrations` pre-commit hook,
refuses edits to any revision that already exists on `origin/main`, so
`git fetch` first.

### 6. Verify It Works

| Check | URL |
|---|---|
| Health (liveness, no database) | http://localhost:8000/api/v1/health |
| Readiness (checks the database) | http://localhost:8000/api/v1/health/ready |
| OpenAPI docs / ReDoc | http://localhost:8000/docs, http://localhost:8000/redoc |
| Milestone | http://localhost:8000/api/v1/meta/milestone (`"milestone":"3"`) |
| Frontend | http://localhost:4200 |
| Postgres (Compose) | `localhost:5432`, user `payroll`, password `payroll_dev_pwd`, database `payroll` |
| Redis (Compose) | `localhost:6379` |

Sign in to the frontend with the seeded development admin:

| Email | Password |
|---|---|
| `admin@payrollfuturistic.co.uk` | `Admin12345!` |

Every endpoint except health, meta and auth needs a bearer token. Get one
(bash / Git Bash):

```bash
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@payrollfuturistic.co.uk","password":"Admin12345!"}'
```

The response has `access_token` (valid 30 minutes), `refresh_token` and
`tenant_id`. Send `Authorization: Bearer <access_token>`; `X-Tenant-ID` is
optional and defaults to the token's tenant.

In Windows PowerShell 5.1 `curl` is an alias for `Invoke-WebRequest`, so use
`curl.exe`, or:

```powershell
$login = Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login -ContentType "application/json" -Body '{"email":"admin@payrollfuturistic.co.uk","password":"Admin12345!"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }
Invoke-RestMethod -Uri http://localhost:8000/api/v1/pay-runs -Headers $headers
```

### 7. Tests and Linters

Backend, as `.github/workflows/ci-backend.yml` runs it (Python 3.12, Postgres 16
service), from `backend/`:

```bash
ruff check app tests
mypy app                 # non-blocking in CI (`|| true`); it currently reports errors
alembic upgrade head
pytest --durations=10
```

Locally `pytest` needs no database: `tests/conftest.py` sets `APP_ENV=test` and
a throwaway SQLite file in the temp directory unless `DATABASE_URL` is already
set. To reproduce CI exactly, run against an empty Postgres database, for
example with the Compose stack up:

```bash
docker compose exec postgres createdb -U payroll payroll_test
export APP_ENV=test
export DATABASE_URL=postgresql+asyncpg://payroll:payroll_dev_pwd@localhost:5432/payroll_test
export DATABASE_URL_SYNC=postgresql+psycopg2://payroll:payroll_dev_pwd@localhost:5432/payroll_test
alembic upgrade head
pytest --durations=10
```

(In PowerShell set the variables with `$env:APP_ENV = "test"` and so on.) CI
runs the suite serially; `pytest-xdist` is installed but CI does not pass `-n`.

Frontend, as `.github/workflows/ci-frontend.yml` runs it (Node 20), from
`frontend/`:

```bash
npm ci
npm test -- --watch=false --browsers=ChromeHeadless   # non-blocking in CI (`|| true`)
npm run build -- --configuration production
```

`npm test` needs Chrome (set `CHROME_BIN` if it is not in the default location).
`npm run lint` exists in `package.json` but fails with `Cannot find "lint"
target` - no ESLint builder is configured in `angular.json` - and CI does not
run it.

Security scans (`.github/workflows/ci-security.yml`, report-only):
`pip install pip-audit` then `pip-audit -r requirements.txt` from `backend/`, and
`npm audit --audit-level=high` from `frontend/`.

Pre-commit hooks, from the repository root:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

### 8. Stop and Reset

| Goal | Command |
|---|---|
| Stop Compose, keep data | `Ctrl+C`, or `docker compose down` (`make down`) |
| Reset the Compose database | `docker compose down -v` (`make clean`) - removes the `pgdata` and `redisdata` volumes; the next `up` re-runs `init.sql`, the migrations and the seed |
| Stop a native run | `Ctrl+C` in the `uvicorn` and `npm start` terminals, then `deactivate` |
| Reset SQLite | Delete `backend/payrollfuturistic-dev.db` |
| Reset native Postgres | `psql -U postgres -c "DROP DATABASE payroll;"`, then repeat the create and migrate steps |

### 9. Troubleshooting

- **`python` opens the Microsoft Store, or `pip install` tries to compile
  `asyncpg` / `psycopg2-binary`.** You are not on Python 3.12. Create the venv
  with `py -3.12 -m venv .venv`; 3.13+ has no wheels for the pinned versions. If
  `Activate.ps1` is blocked ("running scripts is disabled"), run
  `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once. A `.venv` copied
  from another machine fails with `No Python at ...` - delete and recreate it.
- **Login returns 401 but `/api/v1/health` is fine.** `/health` never touches
  the database; check `/api/v1/health/ready`. The admin is only seeded when the
  database is reachable at startup, and a seed that fails is logged as
  `database.seed_failed` with the cause. Fix the database and restart the
  backend. Changing `LOCAL_ADMIN_PASSWORD` later does not update an existing
  user; reset the database instead.
- **`alembic upgrade head` fails with `near "EXTENSION": syntax error`.**
  `DATABASE_URL_SYNC` points at SQLite. The migrations are PostgreSQL-only; with
  SQLite, skip Alembic and just start the backend.
- **The frontend loads but every API call fails.** The development build always
  calls `http://127.0.0.1:8000/api/v1`; `BACKEND_PORT` and
  `FRONTEND_API_BASE_URL` do not change it (nothing reads
  `FRONTEND_API_BASE_URL`). Keep the backend on 8000, and add any other origin
  you serve the frontend from to `APP_CORS_ORIGINS`.
- **`port is already allocated`, or Postgres rejects the password.** Another
  service (often a native PostgreSQL on 5432) holds the port: stop it or change
  `POSTGRES_PORT` / `REDIS_PORT` / `FRONTEND_PORT` in `.env`. `init.sql` and the
  `POSTGRES_*` credentials only apply when the `pgdata` volume is first created;
  after changing them run `docker compose down -v`.
- **Angular CLI refuses your Node version, or new npm packages are missing in
  Compose.** Use Node 20.19+, 22.12+ or 24+. The frontend container keeps
  `node_modules` in an anonymous volume, so after changing
  `frontend/package.json` run `docker compose up --build --renew-anon-volumes`.

## Repository Layout

```text
payroll-engine/
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

Public endpoints:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/meta/milestone
```

Everything else needs the bearer token from
[Verify It Works](#6-verify-it-works):

```bash
TOKEN=<access_token>
curl http://localhost:8000/api/v1/tenants -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/v1/framework -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/v1/pay-runs -H "Authorization: Bearer $TOKEN"
```

Create endpoints accept idempotency:

```bash
curl -X POST http://localhost:8000/api/v1/employees \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-employee-001" \
  -d "{\"first_name\":\"Jane\",\"last_name\":\"Doe\",\"email\":\"jane@example.com\",\"national_insurance_number\":\"AB123456C\",\"tax_code\":\"1257L\",\"employment_start_date\":\"2026-05-01\"}"
```

Give the employee a primary employment contract (use the `id` returned above):

```bash
curl -X POST http://localhost:8000/api/v1/employment-contracts \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-contract-001" \
  -d "{\"employee_id\":\"<employee_id>\",\"contract_type\":\"permanent\",\"pay_frequency\":\"monthly\",\"annual_salary\":\"36000.00\",\"effective_from\":\"2026-05-01\"}"
```

Create a basic payroll run after at least one active employee has a matching
primary employment contract:

```bash
curl -X POST http://localhost:8000/api/v1/pay-runs \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: <tenant_id>" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: demo-pay-run-001" \
  -d "{\"tax_year\":2026,\"period_number\":6,\"pay_frequency\":\"monthly\",\"period_start\":\"2026-06-01\",\"period_end\":\"2026-06-30\",\"payment_date\":\"2026-06-30\",\"adjustments\":[]}"
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

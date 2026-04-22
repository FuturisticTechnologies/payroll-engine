# PayrollFuturistic

A UK-compliant, API-first Payroll SaaS platform by **Snovasys Software Solutions Ltd**.

Aligned with HMRC regulations (PAYE, NI, RTI, statutory payments), pension
auto-enrolment, and UK GDPR.

---

## Status

**Milestone 1 — Project Initiation, Requirement Finalisation, Architecture Design**
(10 Apr 2026 – 30 Apr 2026)

This repository contains the foundational scaffold: runnable backend, runnable
frontend, reference database, architecture and requirement documentation, and
CI/CD pipelines. Every subsequent milestone builds on this base.

See [`docs/`](./docs) for requirements, architecture, data model, HMRC compliance
notes, security/GDPR posture, API design and deployment guides.

---

## Tech stack

| Layer        | Choice                              | Why                                                      |
|--------------|-------------------------------------|----------------------------------------------------------|
| Backend API  | **Python 3.12 + FastAPI**           | Async, typed, API-first, excellent HMRC/integration DX   |
| ORM          | **SQLAlchemy 2.x (async) + Alembic**| Mature, type-safe, migration-driven schema               |
| Frontend     | **Angular 18 (standalone)**         | Enterprise-grade, opinionated, strong typing             |
| Database     | **PostgreSQL 16**                   | Strict types, numeric precision, RLS, JSONB for audit    |
| Cache / Jobs | **Redis 7**                         | Session store, rate limit, background task broker        |
| Auth         | **OAuth2 + JWT (PyJWT)**            | Standard, stateless, SSO-ready                           |
| Runtime      | **Docker Compose**                  | One command brings the whole stack up                    |
| CI           | **GitHub Actions**                  | Lint, test, type-check, SCA, container build             |

See [`docs/02-architecture.md`](./docs/02-architecture.md) for the full picture.

---

## Quick start

### Prerequisites

- Docker Desktop (or Docker Engine + Compose v2)
- Git
- *(Optional for native dev)* Python 3.12, Node 20+, pnpm or npm

### Run the whole stack

```bash
cp .env.example .env
docker compose up --build
```

Then open:

| Service       | URL                             |
|---------------|---------------------------------|
| Frontend      | http://localhost:4200           |
| Backend API   | http://localhost:8000           |
| OpenAPI docs  | http://localhost:8000/docs      |
| Health check  | http://localhost:8000/api/v1/health |
| Postgres      | localhost:5432 (user `payroll`) |

Development admin credentials are seeded automatically in non-production
environments after the database is available:

| Email | Password |
|-------|----------|
| `admin@payrollfuturistic.co.uk` | `Admin12345!` |

Stop with `Ctrl+C` and clean with `docker compose down -v`.

### Run only the backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

### Run only the frontend

```bash
cd frontend
npm install
npm start
```

---

## Repository layout

```
PayrollFuturistic/
├── backend/              FastAPI application, models, migrations, tests
├── frontend/             Angular 18 standalone application
├── docs/                 Architecture, requirements, compliance, API
├── infra/                Database init scripts, local dev infra
├── .github/workflows/    CI pipelines
├── docker-compose.yml    Local orchestration
├── Makefile              Developer shortcuts
└── .env.example          Template environment variables
```

---

## Developer shortcuts

```bash
make up            # docker compose up --build
make down          # docker compose down
make logs          # tail all service logs
make backend-sh    # shell into the backend container
make backend-test  # run backend tests
make frontend-sh   # shell into the frontend container
make migrate       # alembic upgrade head
make lint          # backend + frontend lint
```

---

## Compliance & security

- **HMRC**: PAYE, NI, RTI (FPS/EPS), P60, P45, tax code handling — see
  [`docs/05-hmrc-compliance.md`](./docs/05-hmrc-compliance.md).
- **UK GDPR**: data minimisation, encryption at rest and in transit,
  role-based access control, immutable audit log — see
  [`docs/04-security-gdpr.md`](./docs/04-security-gdpr.md).
- **Statutory payments**: SSP, SMP, SPP — see data model.

---

## License

Proprietary © 2026 Snovasys Software Solutions Ltd. All rights reserved.

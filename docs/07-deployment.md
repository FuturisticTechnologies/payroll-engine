# 07 — Deployment & environments

## 1. Environments

| Env | Purpose | Target stack |
|---|---|---|
| **local** | Developer inner loop | Docker Compose |
| **ci** | PR validation | GitHub Actions runners + ephemeral Postgres |
| **dev** | Integration sandbox | Kubernetes (shared) |
| **staging** | Pre-prod, HMRC **test** API | Kubernetes (isolated namespace) |
| **production** | Live | Kubernetes, multi-AZ |

## 2. Local — Docker Compose

One command:

```bash
cp .env.example .env
docker compose up --build
```

Services:

- `postgres` (16-alpine) on 5432 — init script creates schemas and
  extensions.
- `redis` (7-alpine) on 6379.
- `backend` (FastAPI) on 8000 — runs `alembic upgrade head` then uvicorn.
- `frontend` (Angular dev server) on 4200.

Volumes persist Postgres data between restarts. `make clean` removes them.

## 3. CI — GitHub Actions

Two primary workflows:

- [`ci-backend.yml`](../.github/workflows/ci-backend.yml) — ruff, mypy,
  pytest against an ephemeral Postgres service.
- [`ci-frontend.yml`](../.github/workflows/ci-frontend.yml) — npm install,
  lint, unit tests, production build.

Both run on every PR and on pushes to `main`. Container image builds and
pushes are added from Milestone 2 onwards.

## 4. Container images

### Backend

- Base: `python:3.12-slim`
- Non-root `appuser`
- Includes `curl` for Docker healthcheck
- Dependencies installed into the system site-packages from
  `requirements.txt` (no virtualenv required inside the container)

### Frontend

- Multi-stage build:
  1. `dev` — `node:20-alpine`, live dev server.
  2. `build` — `node:20-alpine`, `ng build --configuration production`.
  3. `prod` — `nginx:1.27-alpine`, serves static bundle with security
     headers and aggressive caching for hashed assets.

## 5. Configuration

All runtime behaviour is driven by environment variables. The backend
validates them via `pydantic-settings` and fails fast on boot if anything
is missing or malformed.

See [`../backend/.env.example`](../backend/.env.example) and the root
[`../.env.example`](../.env.example) for the canonical list.

## 6. Migration strategy

- Alembic owns the schema. Never run raw DDL against an environment.
- Migrations run as part of container startup in dev / staging.
- Production migrations run as a Kubernetes `Job` gated by a manual
  approval in the release workflow (from Milestone 2).
- Backwards-compatible migrations only: add columns/tables before the
  code that uses them, drop after a release cycle.

## 7. Observability (target)

| Signal | Tool |
|---|---|
| Logs | JSON stdout → collector → Loki/ELK |
| Metrics | Prometheus `/metrics` (M12) |
| Traces | OpenTelemetry OTLP → Tempo/Jaeger (M12) |
| Errors | Sentry (M11) |
| Uptime | External synthetic checks on `/api/v1/health` |

## 8. Backup and recovery

- **Postgres**: daily base backup + continuous WAL shipping. 30-day
  point-in-time recovery window.
- **Object storage** (payslips, RTI envelopes): versioned bucket.
- **DR drill**: quarterly restore from backup into a scratch environment.

## 9. Rollout and rollback

- Blue/green or canary deploys with automated rollback on
  error-budget burn (M12).
- Feature flags for risky logic changes (M10).
- Database migrations are designed to support rolling back application
  code without rolling back the schema.

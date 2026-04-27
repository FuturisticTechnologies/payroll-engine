# 10 — Developer workflow

Audience: anyone committing to this repository.

This document exists because the M1 retrospective surfaced the same two
complaints: CI failed on things that could have been caught locally, and it was
unclear which checks were advisory and which were blocking.

## 1. First-time setup

```bash
cp .env.example .env
make up                     # build and start the stack
pip install pre-commit
pre-commit install          # installs the git hook
```

`pre-commit` is optional but strongly recommended — the hooks in
`.pre-commit-config.yaml` are the same checks CI runs, so they turn a
five-minute round trip into a five-second one.

## 2. What blocks a merge

| Gate | Command | Blocking | Notes |
|---|---|---|---|
| Backend lint | `ruff check app tests` | **Yes** | From `backend/` |
| Backend types | `mypy app` | Not in M1 | Strict gate from M2 onward |
| Backend tests | `pytest` | **Yes** | Needs a database from M2 |
| Migrations apply | `alembic upgrade head` | **Yes** | Run against a clean database |
| Frontend lint | `npm run lint` | **Yes** | |
| Frontend tests | `npm test` | **Yes** | Headless Chrome |
| Dependency scan | `ci-security.yml` | No | Report-only until M12 |

The two non-blocking gates are deliberate, not oversights. `mypy` is being
introduced against an existing codebase and would otherwise block every commit
in M1; the SCA scan reports on transitive advisories we do not yet control.
Both are written into the milestone plan with a date attached.

## 3. Conventions that are not negotiable

- **Money is `Decimal`, never `float`.** Binary floating point cannot represent
  a penny exactly. A payroll figure that is out by 0.01 is a defect, not a
  rounding artefact.
- **Migrations are append-only.** Never edit a revision that has been applied to
  any environment — the `alembic_version` table already believes it ran, so the
  edit silently never executes. The `no-edited-migrations` hook enforces this.
- **Every tenant-scoped query goes through the tenant context.** Do not filter
  by `tenant_id` by hand; row-level security is the backstop, not the plan.
- **Commit messages reference the Jira key.** `FPP M1-05: ...` — the milestone
  review reads the git log against the board.

## 4. Branching

Short-lived branches off `main`, named `<jira-key>-<slug>` — for example
`m1-05-fastapi-scaffold`. Squash on merge. `main` is always deployable.

## 5. Running a single test

```bash
cd backend
pytest tests/test_redaction.py -q          # one module
pytest -k "nino" -q                        # one behaviour
```

Tests that do not need a database — the pure calculation, config and redaction
layers — are the ones to reach for while iterating. Anything using the `client`
fixture needs the stack up from M2 onward.

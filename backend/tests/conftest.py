"""Pytest fixtures.

Two things here exist for CI runtime rather than for correctness, and both are
load-bearing enough to explain (M3-12).

**One login per session.** ``auth_headers`` used to log in per test. The login
is a bcrypt verify, which is deliberately slow, and at roughly a quarter of a
second across the pack it was the single largest cost in the suite - larger
than every calculation under test combined. The token is valid for the whole
session, so obtaining it once is not a shortcut, it is the correct scope.

**One database per worker.** Under ``pytest-xdist`` each worker is a separate
process running whole files (``--dist loadfile``), so a shared database would
have workers seeding the default tenant on top of each other. SQLite already
gets a distinct file per process. Postgres does not, so the worker creates its
own database and points itself at it. Without this, parallelising the pack
trades runtime for flakiness, which is not a trade worth making.
"""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

#: Empty for a serial run, ``gw0``/``gw1``/... under xdist.
_WORKER = os.environ.get("PYTEST_XDIST_WORKER", "")

_TEST_DB = Path(gettempdir()) / f"payroll-futuristic-test-{uuid4().hex}.db"
_TEST_DB_URI = _TEST_DB.as_posix()


def _per_worker(url: str) -> str:
    """Give this xdist worker its own Postgres database.

    Returns ``url`` unchanged for a serial run, and for SQLite, whose URL
    already names a file unique to this process.
    """
    if not _WORKER or "postgres" not in url:
        return url

    base, _, database = url.rpartition("/")
    database, sep, query = database.partition("?")
    worker_database = f"{database}_{_WORKER}"

    # Created from the maintenance database, because you cannot CREATE
    # DATABASE from inside the one you are creating.
    from sqlalchemy import create_engine, text

    admin = create_engine(f"{base}/postgres", isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        exists = connection.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": worker_database},
        ).scalar()
        if not exists:
            # Identifier, so it cannot be bound as a parameter. The value is
            # the worker id, which xdist generates - never user input.
            connection.execute(text(f'CREATE DATABASE "{worker_database}"'))
    admin.dispose()

    return f"{base}/{worker_database}{sep}{query}"


os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "APP_SECRET_KEY",
    "test-secret-key-that-is-long-enough-for-validation",
)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_URI}")
os.environ.setdefault("DATABASE_URL_SYNC", f"sqlite:///{_TEST_DB_URI}")
os.environ.setdefault("APP_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200")

if _WORKER:
    os.environ["DATABASE_URL"] = _per_worker(os.environ["DATABASE_URL"])
    os.environ["DATABASE_URL_SYNC"] = _per_worker(os.environ["DATABASE_URL_SYNC"])


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as c:
        yield c

    _TEST_DB.unlink(missing_ok=True)


@pytest.fixture(scope="session")
def _session_auth(client: TestClient) -> dict[str, str]:
    """Log in once. The bcrypt verify is the expensive half of this suite."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@payrollfuturistic.co.uk",
            "password": "Admin12345!",
        },
    )
    assert response.status_code == 200
    body = response.json()
    return {
        "Authorization": f"Bearer {body['access_token']}",
        "X-Tenant-ID": body["tenant_id"],
    }


@pytest.fixture
def auth_headers(_session_auth: dict[str, str]) -> dict[str, str]:
    """A fresh copy of the session token.

    Function-scoped on purpose. The token costs nothing to reuse, but the dict
    does not: a test that adds or overrides a header must not be able to reach
    into the next one.
    """
    return dict(_session_auth)

"""Pytest fixtures."""
from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path
from tempfile import gettempdir
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

_TEST_DB = Path(gettempdir()) / f"payroll-futuristic-test-{uuid4().hex}.db"
_TEST_DB_URI = _TEST_DB.as_posix()

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault(
    "APP_SECRET_KEY",
    "test-secret-key-that-is-long-enough-for-validation",
)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{_TEST_DB_URI}")
os.environ.setdefault("DATABASE_URL_SYNC", f"sqlite:///{_TEST_DB_URI}")
os.environ.setdefault("APP_CORS_ORIGINS", "http://localhost:4200,http://127.0.0.1:4200")


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    from app.main import app

    with TestClient(app) as c:
        yield c

    _TEST_DB.unlink(missing_ok=True)


@pytest.fixture
def auth_headers(client: TestClient) -> dict[str, str]:
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

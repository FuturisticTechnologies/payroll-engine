"""Database-backed smoke tests for the Milestone 1 employee API."""
from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from app.core.config import get_settings
from app.models import Base
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def _employees_table_available() -> bool:
    settings = get_settings()
    engine_kwargs: dict[str, object] = {"future": True}
    if settings.database_url_sync.startswith("postgresql"):
        engine_kwargs["connect_args"] = {"connect_timeout": 1}

    engine = create_engine(settings.database_url_sync, **engine_kwargs)
    try:
        if settings.database_url_sync.startswith("sqlite"):
            Base.metadata.create_all(engine)
        with engine.connect() as connection:
            connection.execute(text("SELECT 1 FROM employees LIMIT 1"))
    except SQLAlchemyError:
        return False
    finally:
        engine.dispose()
    return True


pytestmark = pytest.mark.skipif(
    not _employees_table_available(),
    reason="M1 employees table is not available",
)


def _employee_payload() -> dict[str, object]:
    unique_number = uuid4().int % 1_000_000
    token = uuid4().hex[:10]
    return {
        "first_name": "Milestone",
        "last_name": "One",
        "email": f"m1-{token}@example.com",
        "national_insurance_number": f"AB{unique_number:06d}C",
        "tax_code": "K497",
        "employment_start_date": date(2026, 4, 10).isoformat(),
        "job_title": "Payroll Officer",
    }


def test_ready_probe_reaches_database(client: TestClient) -> None:
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "database": "ok"}


def test_create_employee_persists_validated_record(client: TestClient) -> None:
    payload = _employee_payload()

    created = client.post("/api/v1/employees", json=payload)
    assert created.status_code == 201
    created_body = created.json()
    assert (
        created_body["national_insurance_number"]
        == payload["national_insurance_number"]
    )
    assert created_body["tax_code"] == "K497"

    fetched = client.get(f"/api/v1/employees/{created_body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["email"] == payload["email"]

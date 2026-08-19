"""Liveness + meta endpoint smoke tests."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "PayrollFuturistic API"
    assert "version" in body


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert response.headers["X-Request-ID"]


def test_request_id_header_is_preserved(client: TestClient) -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "m1-check"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "m1-check"


def test_meta_version(client: TestClient) -> None:
    response = client.get("/api/v1/meta/version")
    assert response.status_code == 200
    assert response.json()["service"] == "payroll-futuristic-api"


def test_meta_milestone(client: TestClient) -> None:
    response = client.get("/api/v1/meta/milestone")
    assert response.status_code == 200
    assert response.json()["milestone"] == "3"
    assert response.json()["status"] == "complete"


def test_security_headers_are_present(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]


def test_openapi_schema(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "paths" in response.json()

"""Liveness + meta endpoint smoke tests."""
from __future__ import annotations

from app.core.openapi import OPENAPI_TAGS, SERVICE_TITLE
from fastapi.testclient import TestClient


def test_root(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == SERVICE_TITLE
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


def test_openapi_document_identifies_this_service(client: TestClient) -> None:
    """Every milestone repo publishes the same product at a different point in
    its life. A generic title makes five deployments indistinguishable, so the
    title, the summary and the tag descriptions are part of the contract."""
    document = client.get("/openapi.json").json()

    assert document["info"]["title"] == SERVICE_TITLE
    assert document["info"]["summary"]
    assert document["info"]["description"]

    # Relative, so "Try it out" targets whichever host served the page.
    assert document["servers"] == [{"url": "/", "description": "This deployment."}]

    documented = {tag["name"] for tag in document["tags"]}
    assert documented == {tag["name"] for tag in OPENAPI_TAGS}
    assert all(tag["description"] for tag in document["tags"])

    # Every tag the router mounts must be described, or the UI renders a
    # heading with nothing under it explaining what the group is for.
    used = {tag for path in document["paths"].values()
            for operation in path.values()
            for tag in operation.get("tags", [])}
    assert used <= documented, f"undocumented tags: {sorted(used - documented)}"

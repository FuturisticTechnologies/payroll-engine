"""Paging parameters on the list endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

LIST_ENDPOINTS = [
    "/api/v1/employees",
    "/api/v1/employment-contracts",
    "/api/v1/pay-runs",
    "/api/v1/tenants",
]

OUT_OF_RANGE = [
    "limit=-1",
    "limit=0",
    "limit=501",
    "limit=100000000000000000000",
    "offset=-1",
    "offset=100000000000000000000",
]


@pytest.mark.parametrize("query", OUT_OF_RANGE)
@pytest.mark.parametrize("path", LIST_ENDPOINTS)
def test_out_of_range_paging_is_a_validation_error(
    client: TestClient,
    auth_headers: dict[str, str],
    path: str,
    query: str,
) -> None:
    """Rejected before it reaches SQL, where it was an unbounded or failed query."""
    response = client.get(f"{path}?{query}", headers=auth_headers)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("path", LIST_ENDPOINTS)
def test_paging_at_the_bounds_is_accepted(
    client: TestClient,
    auth_headers: dict[str, str],
    path: str,
) -> None:
    response = client.get(f"{path}?limit=500&offset=0", headers=auth_headers)
    assert response.status_code == 200, response.text
    assert isinstance(response.json(), list)

"""Pytest fixtures.

The Milestone 1 smoke tests do not require a real database — they exercise
the pure-Python layers (config, schema validation, routing). Later milestones
will add an ephemeral Postgres fixture via testcontainers.
"""
from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    # Import lazily so env is set up by the time the app boots.
    from app.main import app

    with TestClient(app) as c:
        yield c

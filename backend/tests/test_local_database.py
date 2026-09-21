"""The startup seed in ``init_local_database``.

Without it nobody can log in, and it runs before the app serves anything, so
it has to cope with row-level security and must never fail silently.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from app.core import database
from app.core.payroll_framework import DEFAULT_TENANT_ID
from fastapi.testclient import TestClient
from sqlalchemy.exc import ProgrammingError


class _RecordingLog:
    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def warning(self, event: str, **_: Any) -> None:
        self.records.append(("warning", event))

    def exception(self, event: str, **_: Any) -> None:
        self.records.append(("error", event))


@pytest.fixture
def recording_log(monkeypatch: pytest.MonkeyPatch) -> _RecordingLog:
    recorder = _RecordingLog()
    monkeypatch.setattr(database, "log", recorder)
    return recorder


def _session_factory_raising(exc: BaseException) -> Any:
    def factory() -> Any:
        raise exc

    return factory


def test_seed_runs_under_the_default_tenant_context(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    recording_log: _RecordingLog,
) -> None:
    # tenants and user_tenant_roles use FORCE ROW LEVEL SECURITY, so on
    # Postgres without a superuser the seed only sees its own tenant's rows.
    #
    # Driven through the client's portal rather than as an async test: the
    # engine's pooled asyncpg connections belong to the loop the app started
    # on, and awaiting them from a second loop fails with "attached to a
    # different loop". SQLite does not care, so a bare async test passes
    # locally and fails against CI's Postgres.
    contexts: list[UUID] = []
    set_tenant_context = database.set_tenant_context

    async def spy(session: Any, tenant_id: UUID, **kwargs: Any) -> None:
        contexts.append(tenant_id)
        await set_tenant_context(session, tenant_id, **kwargs)

    monkeypatch.setattr(database, "set_tenant_context", spy)

    client.portal.call(database.init_local_database)

    assert contexts == [DEFAULT_TENANT_ID]
    assert recording_log.records == []


async def test_failed_seed_is_logged_as_an_error(
    monkeypatch: pytest.MonkeyPatch,
    recording_log: _RecordingLog,
) -> None:
    rls_violation = ProgrammingError(
        "INSERT INTO tenants ...",
        {},
        Exception('new row violates row-level security policy for table "tenants"'),
    )
    monkeypatch.setattr(database, "is_sqlite", False)
    monkeypatch.setattr(
        database, "AsyncSessionLocal", _session_factory_raising(rls_violation)
    )

    await database.init_local_database()

    assert recording_log.records == [("error", "database.seed_failed")]


async def test_unreachable_database_does_not_stop_startup(
    monkeypatch: pytest.MonkeyPatch,
    recording_log: _RecordingLog,
) -> None:
    # asyncpg raises this unwrapped, not as a SQLAlchemyError, when nothing
    # listens on the Postgres port.
    refused = ConnectionRefusedError(10061, "Connect call failed ('127.0.0.1', 5432)")
    monkeypatch.setattr(database, "is_sqlite", False)
    monkeypatch.setattr(database, "AsyncSessionLocal", _session_factory_raising(refused))

    await database.init_local_database()

    assert recording_log.records == [("warning", "database.seed_skipped_unreachable")]

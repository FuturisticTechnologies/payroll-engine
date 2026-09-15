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


async def test_seed_runs_under_the_default_tenant_context(
    monkeypatch: pytest.MonkeyPatch,
    recording_log: _RecordingLog,
) -> None:
    # tenants and user_tenant_roles use FORCE ROW LEVEL SECURITY, so on
    # Postgres without a superuser the seed only sees its own tenant's rows.
    contexts: list[UUID] = []
    set_tenant_context = database.set_tenant_context

    async def spy(session: Any, tenant_id: UUID, **kwargs: Any) -> None:
        contexts.append(tenant_id)
        await set_tenant_context(session, tenant_id, **kwargs)

    monkeypatch.setattr(database, "set_tenant_context", spy)

    await database.init_local_database()

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

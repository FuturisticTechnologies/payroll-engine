"""Statutory reference data through the database (SNOV-442).

The local app seeds ``statutory_payment_rates`` from the reviewed CSV; on
Postgres the M8 migration does. Either way the loader must return the rows in
force on the date asked for.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.core.database import AsyncSessionLocal
from app.core.statutory_pay import StatutoryReferenceError
from app.core.statutory_reference import load_statutory_rates, read_seed_rows
from app.models.statutory import StatutoryPaymentRate
from fastapi.testclient import TestClient
from sqlalchemy import func, select


async def _count() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(StatutoryPaymentRate.id)))
        return int(result.scalar_one())


async def _weekly_flat(scheme: str, on: date) -> list[Decimal | None]:
    async with AsyncSessionLocal() as session:
        return [row.weekly_flat_rate for row in await load_statutory_rates(session, scheme, on)]


async def _missing() -> None:
    async with AsyncSessionLocal() as session:
        await load_statutory_rates(session, "SSP", date(2030, 1, 1))


def test_reference_rows_are_seeded(client: TestClient) -> None:
    # Driven through the app's portal: pooled connections belong to its loop.
    assert client.portal is not None
    assert client.portal.call(_count) == len(read_seed_rows())


def test_loader_resolves_by_pay_date(client: TestClient) -> None:
    assert client.portal is not None
    assert client.portal.call(_weekly_flat, "SSP", date(2026, 3, 31)) == [Decimal("118.75")]
    assert client.portal.call(_weekly_flat, "SSP", date(2026, 4, 6)) == [Decimal("123.25")]
    assert client.portal.call(_weekly_flat, "SMP", date(2026, 6, 1)) == [None, Decimal("194.32")]


def test_loader_refuses_a_date_with_no_data(client: TestClient) -> None:
    assert client.portal is not None
    try:
        client.portal.call(_missing)
    except StatutoryReferenceError as exc:
        assert "no SSP reference data in force" in str(exc)
    else:
        raise AssertionError("expected StatutoryReferenceError")

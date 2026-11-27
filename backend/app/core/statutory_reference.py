"""Load statutory payment reference data for the date a payment relates to.

The database side of ``app.core.statutory_pay``: read the rows in force for a
scheme on a given date and hand them to the pure calculation functions. Pass
the pay period's date (or the absence / leave week being paid), never
``date.today()`` - that is what keeps a recalculated prior period on the
values that were in force then.
"""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.statutory_pay import StatutoryRate, rates_in_force
from app.models.statutory import StatutoryPaymentRate

#: The reviewed source the migration seed and the local SQLite seed are built
#: from. ``tests/test_statutory_reference.py`` keeps the three in step.
SEED_CSV = Path(__file__).resolve().parents[1] / "reference_data" / "statutory_payment_rates.csv"

_FIELDS = [
    column.name
    for column in StatutoryPaymentRate.__table__.columns
    if column.name not in {"id", "created_at", "updated_at"}
]


def read_seed_rows(path: Path = SEED_CSV) -> list[StatutoryRate]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [StatutoryRate.from_mapping(row) for row in csv.DictReader(handle)]


async def load_statutory_rates(db: AsyncSession, scheme: str, on: date) -> list[StatutoryRate]:
    """Rows for ``scheme`` in force on ``on``; raises if none or ambiguous."""
    result = await db.execute(
        select(StatutoryPaymentRate).where(
            StatutoryPaymentRate.scheme == scheme,
            StatutoryPaymentRate.effective_from <= on,
            or_(
                StatutoryPaymentRate.effective_to.is_(None),
                StatutoryPaymentRate.effective_to >= on,
            ),
        )
    )
    rows = [
        StatutoryRate.from_mapping({field: getattr(orm, field) for field in _FIELDS})
        for orm in result.scalars()
    ]
    return rates_in_force(rows, scheme, on)


async def seed_local_statutory_rates(db: AsyncSession) -> int:
    """Insert the seed rows into an empty local database. Returns rows added.

    For local SQLite only - Postgres environments get the rows from the
    Alembic migration, which is the record of what was applied where.
    """
    existing = await db.execute(select(StatutoryPaymentRate.id).limit(1))
    if existing.first() is not None:
        return 0
    rows = read_seed_rows()
    for row in rows:
        db.add(StatutoryPaymentRate(**{field: getattr(row, field) for field in _FIELDS}))
    await db.flush()
    return len(rows)

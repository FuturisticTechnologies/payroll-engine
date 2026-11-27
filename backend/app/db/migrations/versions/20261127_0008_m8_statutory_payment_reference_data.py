"""M8 statutory payment reference data: SSP, SMP and SPP for 2025/26 and 2026/27.

SNOV-442. Effective-dated rates, thresholds and limits for Statutory Sick Pay,
Statutory Maternity Pay and Statutory Paternity Pay, so the statutory
calculations read them by pay date instead of holding constants in code.

2025/26 is seeded alongside 2026/27 so that a pay run for a period before
6 April 2026 resolves to the values in force at the time. That matters most
for SSP, where the Employment Rights Act 2025 removed the three waiting days
and the lower earnings limit from 6 April 2026 and introduced the 80% of
average weekly earnings cap.

The rows are written out here rather than read from
``app/reference_data/statutory_payment_rates.csv`` so this revision stays
exactly what was applied even after the CSV moves on to later years.
``tests/test_statutory_reference.py`` checks the two match.

Sources (every row also carries its own ``source_reference`` and ``source_url``):
- https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026
- https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027

Revision ID: 20261127_0008
Revises: 20260601_0003
Create Date: 2026-11-27
"""
# ruff: noqa: E501 - the seed rows carry full HMRC source citations
from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261127_0008"
# NOTE: points at the latest revision on development. If the M4 PAYE and M5 NI
# reference-data revisions land first, re-point this at their head before
# merging so Alembic keeps a single head.
down_revision: str | None = "20260601_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "statutory_payment_rates"

SEED_ROWS: list[dict[str, object]] = [
    {
        "tax_year": 2025,
        "scheme": "SSP",
        "rate_period": "standard",
        "period_start_week": 1,
        "period_end_week": 28,
        "effective_from": date.fromisoformat("2025-04-06"),
        "effective_to": date.fromisoformat("2026-04-05"),
        "awe_percentage": None,
        "weekly_flat_rate": Decimal("118.75"),
        "rate_rule": "flat_rate_only",
        "lower_earnings_limit_weekly": Decimal("125.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": None,
        "continuous_employment_weeks": None,
        "waiting_days": 3,
        "max_entitlement_weeks": 28,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2025 to 2026, Statutory Sick Pay; Class 1 NI lower earnings limit",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026",
    },
    {
        "tax_year": 2025,
        "scheme": "SMP",
        "rate_period": "first_6_weeks",
        "period_start_week": 1,
        "period_end_week": 6,
        "effective_from": date.fromisoformat("2025-04-06"),
        "effective_to": date.fromisoformat("2026-04-04"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": None,
        "rate_rule": "percentage_only",
        "lower_earnings_limit_weekly": Decimal("125.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 39,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2025 to 2026, Statutory Maternity Pay first 6 weeks",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026",
    },
    {
        "tax_year": 2025,
        "scheme": "SMP",
        "rate_period": "remaining_weeks",
        "period_start_week": 7,
        "period_end_week": 39,
        "effective_from": date.fromisoformat("2025-04-06"),
        "effective_to": date.fromisoformat("2026-04-04"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": Decimal("187.18"),
        "rate_rule": "lower_of_flat_and_percentage",
        "lower_earnings_limit_weekly": Decimal("125.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 39,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2025 to 2026, Statutory Maternity Pay remaining weeks",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026",
    },
    {
        "tax_year": 2025,
        "scheme": "SPP",
        "rate_period": "standard",
        "period_start_week": 1,
        "period_end_week": 2,
        "effective_from": date.fromisoformat("2025-04-06"),
        "effective_to": date.fromisoformat("2026-04-05"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": Decimal("187.18"),
        "rate_rule": "lower_of_flat_and_percentage",
        "lower_earnings_limit_weekly": Decimal("125.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 2,
        "payment_window_weeks": 52,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2025 to 2026, Statutory Paternity Pay",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2025-to-2026",
    },
    {
        "tax_year": 2026,
        "scheme": "SSP",
        "rate_period": "standard",
        "period_start_week": 1,
        "period_end_week": 28,
        "effective_from": date.fromisoformat("2026-04-06"),
        "effective_to": date.fromisoformat("2027-04-05"),
        "awe_percentage": Decimal("0.8000"),
        "weekly_flat_rate": Decimal("123.25"),
        "rate_rule": "lower_of_flat_and_percentage",
        "lower_earnings_limit_weekly": None,
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": None,
        "continuous_employment_weeks": None,
        "waiting_days": 0,
        "max_entitlement_weeks": 28,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2026 to 2027, Statutory Sick Pay; Employment Rights Act 2025 removes waiting days and the lower earnings limit from 6 April 2026",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027",
    },
    {
        "tax_year": 2026,
        "scheme": "SMP",
        "rate_period": "first_6_weeks",
        "period_start_week": 1,
        "period_end_week": 6,
        "effective_from": date.fromisoformat("2026-04-05"),
        "effective_to": date.fromisoformat("2027-04-03"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": None,
        "rate_rule": "percentage_only",
        "lower_earnings_limit_weekly": Decimal("129.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 39,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2026 to 2027, Statutory Maternity Pay first 6 weeks (SMP rate applies from 5 April 2026)",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027",
    },
    {
        "tax_year": 2026,
        "scheme": "SMP",
        "rate_period": "remaining_weeks",
        "period_start_week": 7,
        "period_end_week": 39,
        "effective_from": date.fromisoformat("2026-04-05"),
        "effective_to": date.fromisoformat("2027-04-03"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": Decimal("194.32"),
        "rate_rule": "lower_of_flat_and_percentage",
        "lower_earnings_limit_weekly": Decimal("129.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 39,
        "payment_window_weeks": None,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2026 to 2027, Statutory Maternity Pay remaining weeks (SMP rate applies from 5 April 2026)",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027",
    },
    {
        "tax_year": 2026,
        "scheme": "SPP",
        "rate_period": "standard",
        "period_start_week": 1,
        "period_end_week": 2,
        "effective_from": date.fromisoformat("2026-04-06"),
        "effective_to": date.fromisoformat("2027-04-05"),
        "awe_percentage": Decimal("0.9000"),
        "weekly_flat_rate": Decimal("194.32"),
        "rate_rule": "lower_of_flat_and_percentage",
        "lower_earnings_limit_weekly": Decimal("129.00"),
        "relevant_period_weeks": 8,
        "qualifying_week_offset_weeks": 15,
        "continuous_employment_weeks": 26,
        "waiting_days": 0,
        "max_entitlement_weeks": 2,
        "payment_window_weeks": 52,
        "rounding": "round_up_penny",
        "source_reference": "HMRC Rates and thresholds for employers 2026 to 2027, Statutory Paternity Pay; 26-week service test for pay unchanged by Employment Rights Act 2025",
        "source_url": "https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027",
    },
]


def upgrade() -> None:
    table = op.create_table(
        TABLE,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("scheme", sa.String(length=3), nullable=False),
        sa.Column("rate_period", sa.String(length=30), nullable=False),
        sa.Column("period_start_week", sa.Integer(), nullable=False),
        sa.Column("period_end_week", sa.Integer(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("awe_percentage", sa.Numeric(5, 4), nullable=True),
        sa.Column("weekly_flat_rate", sa.Numeric(10, 2), nullable=True),
        sa.Column("rate_rule", sa.String(length=40), nullable=False),
        sa.Column("lower_earnings_limit_weekly", sa.Numeric(10, 2), nullable=True),
        sa.Column("relevant_period_weeks", sa.Integer(), nullable=False),
        sa.Column("qualifying_week_offset_weeks", sa.Integer(), nullable=True),
        sa.Column("continuous_employment_weeks", sa.Integer(), nullable=True),
        sa.Column("waiting_days", sa.Integer(), nullable=False),
        sa.Column("max_entitlement_weeks", sa.Integer(), nullable=False),
        sa.Column("payment_window_weeks", sa.Integer(), nullable=True),
        sa.Column("rounding", sa.String(length=30), nullable=False),
        sa.Column("source_reference", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(length=300), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "scheme",
            "rate_period",
            "effective_from",
            name="uq_statutory_payment_rates_scheme_period_from",
        ),
        sa.CheckConstraint("scheme IN ('SSP', 'SMP', 'SPP')", name="ck_statutory_rates_scheme"),
        sa.CheckConstraint(
            "rate_rule IN ('flat_rate_only', 'percentage_only', 'lower_of_flat_and_percentage')",
            name="ck_statutory_rates_rule",
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_statutory_rates_dates",
        ),
        sa.CheckConstraint(
            "awe_percentage IS NULL OR (awe_percentage > 0 AND awe_percentage <= 1)",
            name="ck_statutory_rates_awe_percentage",
        ),
        sa.CheckConstraint(
            "period_end_week >= period_start_week", name="ck_statutory_rates_weeks"
        ),
    )
    op.create_index("ix_statutory_payment_rates_tax_year", TABLE, ["tax_year"])
    op.create_index(
        "ix_statutory_payment_rates_scheme_effective",
        TABLE,
        ["scheme", "effective_from", "effective_to"],
    )

    # Two rows for the same scheme and rate period must never be in force on
    # the same day, or a pay run could pick either. btree_gist is created by
    # the M2 revision for the employment contract constraint.
    op.execute(
        f"""
        ALTER TABLE {TABLE}
        ADD CONSTRAINT ex_statutory_payment_rates_no_overlap
        EXCLUDE USING gist (
            scheme WITH =,
            rate_period WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[]') WITH &&
        )
        """
    )

    op.bulk_insert(table, SEED_ROWS)


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE {TABLE} DROP CONSTRAINT IF EXISTS ex_statutory_payment_rates_no_overlap"
    )
    op.drop_index("ix_statutory_payment_rates_scheme_effective", table_name=TABLE)
    op.drop_index("ix_statutory_payment_rates_tax_year", table_name=TABLE)
    op.drop_table(TABLE)

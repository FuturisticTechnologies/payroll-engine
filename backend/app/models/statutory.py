"""Effective-dated statutory payment reference data (SNOV-442).

HMRC reference data, not tenant data: the same SSP, SMP and SPP rates apply to
every employer, so the table has no ``tenant_id`` and no row-level security.
Rows are never updated in place. A new tax year is a new row with a new
``effective_from``, which is what lets a prior period be recalculated with the
values that were in force at the time.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class StatutoryPaymentRate(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "statutory_payment_rates"
    __table_args__ = (
        UniqueConstraint(
            "scheme",
            "rate_period",
            "effective_from",
            name="uq_statutory_payment_rates_scheme_period_from",
        ),
        CheckConstraint("scheme IN ('SSP', 'SMP', 'SPP')", name="ck_statutory_rates_scheme"),
        CheckConstraint(
            "rate_rule IN ('flat_rate_only', 'percentage_only', 'lower_of_flat_and_percentage')",
            name="ck_statutory_rates_rule",
        ),
        CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_statutory_rates_dates",
        ),
        CheckConstraint(
            "awe_percentage IS NULL OR (awe_percentage > 0 AND awe_percentage <= 1)",
            name="ck_statutory_rates_awe_percentage",
        ),
        CheckConstraint(
            "period_end_week >= period_start_week", name="ck_statutory_rates_weeks"
        ),
    )

    tax_year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    scheme: Mapped[str] = mapped_column(String(3), nullable=False)
    rate_period: Mapped[str] = mapped_column(String(30), nullable=False)
    period_start_week: Mapped[int] = mapped_column(Integer, nullable=False)
    period_end_week: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    awe_percentage: Mapped[Decimal | None] = mapped_column(Numeric(5, 4), nullable=True)
    weekly_flat_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    rate_rule: Mapped[str] = mapped_column(String(40), nullable=False)
    lower_earnings_limit_weekly: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2), nullable=True
    )
    relevant_period_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    qualifying_week_offset_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    continuous_employment_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    waiting_days: Mapped[int] = mapped_column(Integer, nullable=False)
    max_entitlement_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    payment_window_weeks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rounding: Mapped[str] = mapped_column(String(30), nullable=False)
    source_reference: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(String(300), nullable=False)

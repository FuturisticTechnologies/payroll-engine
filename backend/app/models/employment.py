"""Employment contract baseline for payroll framework setup."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class EmploymentContract(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "employment_contracts"
    __table_args__ = (
        UniqueConstraint(
            "employee_id",
            "effective_from",
            name="uq_employment_contracts_employee_effective_from",
        ),
        Index(
            "uq_employment_contracts_employee_primary",
            "employee_id",
            unique=True,
            postgresql_where=text("is_primary"),
            sqlite_where=text("is_primary"),
        ),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_type: Mapped[str] = mapped_column(
        String(32), nullable=False, default="permanent"
    )
    pay_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    annual_salary: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    weekly_hours: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="GBP")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

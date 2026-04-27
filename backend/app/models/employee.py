"""Employee core record.

Milestone 1 establishes the minimum fields needed for a PAYE-compliant
employee record: identity, NI number, tax code, start date. Pay-affecting
components (salary, benefits, deductions, pension) arrive in later
milestones together with their validation and ledger logic.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Employee(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "employees"

    # ---------- Identity ----------
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)

    # ---------- HMRC ----------
    # UK NI numbers: 2 letters, 6 digits, 1 letter (e.g. AB123456C).
    # Validated at schema layer, stored upper-cased.
    national_insurance_number: Mapped[str] = mapped_column(
        String(9), nullable=False, unique=True, index=True
    )
    # Tax codes: 1257L, BR, D0, NT, etc. - free-form 2-10 chars for now.
    tax_code: Mapped[str] = mapped_column(String(10), nullable=False, default="1257L")

    # ---------- Employment ----------
    employment_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(150), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Employee id={self.id} name={self.first_name} {self.last_name} "
            f"ni={self.national_insurance_number}>"
        )

"""Employer tenant model introduced in Milestone 2."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Tenant(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    company_registration_number: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    paye_reference: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accounts_office_reference: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )
    default_pay_frequency: Mapped[str] = mapped_column(
        String(20), nullable=False, default="monthly"
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug}>"

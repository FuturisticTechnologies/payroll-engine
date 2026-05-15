"""Milestone 2 role-based access control tables."""
from __future__ import annotations

import uuid

from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPkMixin


class Role(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("code", name="uq_roles_code"),)

    code: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Permission(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "permissions"
    __table_args__ = (UniqueConstraint("code", name="uq_permissions_code"),)

    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(255), nullable=False)


class RolePermission(UUIDPkMixin, Base):
    __tablename__ = "role_permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )

    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False, index=True
    )


class UserTenantRole(UUIDPkMixin, TimestampMixin, Base):
    __tablename__ = "user_tenant_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "tenant_id", "role_id", name="uq_user_tenant_role"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

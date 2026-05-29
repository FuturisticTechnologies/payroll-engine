"""Async database engine, session factory and FastAPI dependency."""
from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.models import Base
from app.models.user import User

settings = get_settings()

is_sqlite = settings.database_url.startswith("sqlite")

engine_kwargs = {
    "echo": settings.app_debug,
    "future": True,
}
if is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

engine = create_async_engine(settings.database_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that yields a scoped async session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await clear_tenant_context(session)
            await session.close()


async def set_tenant_context(
    session: AsyncSession,
    tenant_id: UUID,
    *,
    is_superuser: bool = False,
) -> None:
    """Set the Postgres tenant context used by row-level security policies."""
    if is_sqlite:
        return
    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    await session.execute(
        text("SELECT set_config('app.is_superuser', :is_superuser, true)"),
        {"is_superuser": "true" if is_superuser else "false"},
    )


async def clear_tenant_context(session: AsyncSession) -> None:
    """Clear tenant context before returning pooled Postgres connections."""
    if is_sqlite:
        return
    try:
        await session.execute(
            text("SELECT set_config('app.tenant_id', '', true)")
        )
        await session.execute(
            text("SELECT set_config('app.is_superuser', 'false', true)")
        )
    except SQLAlchemyError:
        return


async def init_local_database() -> None:
    """Create SQLite tables and seed a development admin when possible."""
    if settings.app_env == "production":
        return

    from app.core.payroll_framework import (
        DEFAULT_TENANT,
        DEFAULT_TENANT_ID,
        ROLE_PERMISSION_CODES,
        SYSTEM_PERMISSIONS,
        SYSTEM_ROLES,
    )
    from app.core.security import hash_password
    from app.models.rbac import Permission, Role, RolePermission, UserTenantRole
    from app.models.tenant import Tenant

    try:
        if is_sqlite:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)
                await _migrate_sqlite_m2(connection)

        async with AsyncSessionLocal() as session:
            tenant = await session.get(Tenant, DEFAULT_TENANT_ID)
            if tenant is None:
                result = await session.execute(
                    select(Tenant).where(Tenant.slug == DEFAULT_TENANT["slug"])
                )
                tenant = result.scalar_one_or_none()
            if tenant is None:
                tenant = Tenant(**DEFAULT_TENANT)
                session.add(tenant)
                await session.flush()

            role_by_code: dict[str, Role] = {}
            for role_data in SYSTEM_ROLES:
                result = await session.execute(
                    select(Role).where(Role.code == role_data["code"])
                )
                role = result.scalar_one_or_none()
                if role is None:
                    role = Role(**role_data)
                    session.add(role)
                    await session.flush()
                role_by_code[role.code] = role

            permission_by_code: dict[str, Permission] = {}
            for permission_data in SYSTEM_PERMISSIONS:
                result = await session.execute(
                    select(Permission).where(Permission.code == permission_data["code"])
                )
                permission = result.scalar_one_or_none()
                if permission is None:
                    permission = Permission(**permission_data)
                    session.add(permission)
                    await session.flush()
                permission_by_code[permission.code] = permission

            for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
                role = role_by_code[role_code]
                for permission_code in permission_codes:
                    permission = permission_by_code[permission_code]
                    result = await session.execute(
                        select(RolePermission).where(
                            RolePermission.role_id == role.id,
                            RolePermission.permission_id == permission.id,
                        )
                    )
                    if result.scalar_one_or_none() is None:
                        session.add(
                            RolePermission(
                                role_id=role.id,
                                permission_id=permission.id,
                            )
                        )

            result = await session.execute(
                select(User).where(User.email == settings.local_admin_email)
            )
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    email=settings.local_admin_email,
                    full_name="Local Administrator",
                    hashed_password=hash_password(settings.local_admin_password),
                    role="super_admin",
                    is_active=True,
                    is_superuser=True,
                )
                session.add(user)
                await session.flush()

            tenant_owner = role_by_code["tenant_owner"]
            result = await session.execute(
                select(UserTenantRole).where(
                    UserTenantRole.user_id == user.id,
                    UserTenantRole.tenant_id == tenant.id,
                    UserTenantRole.role_id == tenant_owner.id,
                )
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    UserTenantRole(
                        user_id=user.id,
                        tenant_id=tenant.id,
                        role_id=tenant_owner.id,
                        is_active=True,
                    )
                )

            await session.commit()
    except SQLAlchemyError:
        # Liveness can still pass when a native dev database is not running;
        # readiness remains the source of truth for DB availability.
        return


async def _migrate_sqlite_m2(connection) -> None:  # type: ignore[no-untyped-def]
    """Patch an existing local SQLite M1 database into the M2 shape."""
    from app.core.payroll_framework import DEFAULT_TENANT_ID

    result = await connection.execute(text("PRAGMA table_info(employees)"))
    columns = {row[1] for row in result.fetchall()}
    if not columns:
        return

    additions = {
        "tenant_id": "ALTER TABLE employees ADD COLUMN tenant_id CHAR(32)",
        "employee_number": "ALTER TABLE employees ADD COLUMN employee_number VARCHAR(40)",
        "ni_category": (
            "ALTER TABLE employees ADD COLUMN ni_category VARCHAR(1) NOT NULL DEFAULT 'A'"
        ),
        "employment_status": (
            "ALTER TABLE employees ADD COLUMN employment_status VARCHAR(20) "
            "NOT NULL DEFAULT 'active'"
        ),
    }
    for column, statement in additions.items():
        if column not in columns:
            await connection.execute(text(statement))

    await connection.execute(
        text(
            "UPDATE employees SET tenant_id = :tenant_id "
            "WHERE tenant_id IS NULL OR tenant_id = ''"
        ),
        {"tenant_id": DEFAULT_TENANT_ID.hex},
    )
    await connection.execute(
        text(
            "UPDATE employees "
            "SET employee_number = 'EMP-' || upper(substr(hex(randomblob(4)), 1, 8)) "
            "WHERE employee_number IS NULL OR employee_number = ''"
        )
    )

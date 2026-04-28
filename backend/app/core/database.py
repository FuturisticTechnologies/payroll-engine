"""Async database engine, session factory and FastAPI dependency."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy import select
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
            await session.close()


async def init_local_database() -> None:
    """Create SQLite tables and seed a development admin when possible."""
    if settings.app_env == "production":
        return

    from app.core.security import hash_password

    try:
        if is_sqlite:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.email == settings.local_admin_email)
            )
            if result.scalar_one_or_none() is None:
                session.add(
                    User(
                        email=settings.local_admin_email,
                        full_name="Local Administrator",
                        hashed_password=hash_password(settings.local_admin_password),
                        role="super_admin",
                        is_active=True,
                        is_superuser=True,
                    )
                )
                await session.commit()
    except SQLAlchemyError:
        # Liveness can still pass when a native dev database is not running;
        # readiness remains the source of truth for DB availability.
        return

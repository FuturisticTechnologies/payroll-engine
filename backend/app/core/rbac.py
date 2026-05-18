"""Authentication, RBAC and tenant context dependencies."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

import jwt
from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, set_tenant_context
from app.core.payroll_framework import DEFAULT_TENANT_ID, SYSTEM_PERMISSIONS
from app.core.security import decode_token
from app.models.rbac import Permission, Role, RolePermission, UserTenantRole
from app.models.tenant import Tenant
from app.models.user import User

_bearer = HTTPBearer(auto_error=False)
_SYSTEM_PERMISSION_CODES = {permission["code"] for permission in SYSTEM_PERMISSIONS}


@dataclass
class AccessContext:
    user: User
    tenant_id: UUID
    permissions: set[str]
    db: AsyncSession


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _tenant_from_header_or_claim(
    x_tenant_id: str | None,
    claim_tenant_id: object,
) -> UUID:
    raw_tenant_id = x_tenant_id or claim_tenant_id or str(DEFAULT_TENANT_ID)
    try:
        return UUID(str(raw_tenant_id))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid tenant id",
        ) from exc


async def _permission_codes_for_user(
    db: AsyncSession,
    user_id: UUID,
    tenant_id: UUID,
) -> set[str]:
    stmt = (
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(UserTenantRole, UserTenantRole.role_id == Role.id)
        .where(
            UserTenantRole.user_id == user_id,
            UserTenantRole.tenant_id == tenant_id,
            UserTenantRole.is_active.is_(True),
        )
    )
    result = await db.execute(stmt)
    return set(result.scalars().all())


async def current_access_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
) -> AccessContext:
    if credentials is None:
        raise _unauthorized()
    try:
        claims = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _unauthorized() from exc

    if claims.get("type") != "access":
        raise _unauthorized()

    try:
        user_id = UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise _unauthorized() from exc

    user = await db.get(User, user_id)
    if user is None:
        raise _unauthorized()
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    tenant_id = _tenant_from_header_or_claim(x_tenant_id, claims.get("tenant_id"))
    await set_tenant_context(db, tenant_id, is_superuser=user.is_superuser)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise _unauthorized()

    if user.is_superuser:
        permissions = set(_SYSTEM_PERMISSION_CODES)
    else:
        permissions = await _permission_codes_for_user(db, user.id, tenant_id)

    request.state.tenant_id = tenant_id
    request.state.user_id = user.id
    return AccessContext(
        user=user,
        tenant_id=tenant_id,
        permissions=permissions,
        db=db,
    )


def require_permission(permission: str) -> Callable[..., object]:
    async def dependency(
        access: AccessContext = Depends(current_access_context),
    ) -> AccessContext:
        if permission not in access.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return access

    return dependency

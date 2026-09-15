"""Authentication endpoints."""
from __future__ import annotations

from secrets import token_urlsafe

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, set_tenant_context
from app.core.payroll_framework import DEFAULT_TENANT_ID, SYSTEM_PERMISSIONS
from app.core.rbac import _permission_codes_for_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
)
from app.models.user import User
from app.schemas.auth import CsrfTokenResponse, LoginRequest, TokenResponse

router = APIRouter()
settings = get_settings()
_SYSTEM_PERMISSION_CODES = sorted(permission["code"] for permission in SYSTEM_PERMISSIONS)


@router.get("/csrf", response_model=CsrfTokenResponse)
async def csrf_token(response: Response) -> CsrfTokenResponse:
    token = token_urlsafe(32)
    response.set_cookie(
        "csrf_token",
        token,
        secure=settings.app_env == "production",
        httponly=False,
        samesite="strict",
        path="/",
    )
    return CsrfTokenResponse(csrf_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    from sqlalchemy import func, select

    stmt = select(User).where(func.lower(User.email) == payload.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is disabled",
        )

    tenant_id = DEFAULT_TENANT_ID
    await set_tenant_context(db, tenant_id, is_superuser=user.is_superuser)
    if user.is_superuser:
        permissions = _SYSTEM_PERMISSION_CODES
    else:
        permissions = sorted(await _permission_codes_for_user(db, user.id, tenant_id))

    claims = {
        "role": user.role,
        "tenant_id": str(tenant_id),
        "permissions": permissions,
    }
    return TokenResponse(
        access_token=create_access_token(str(user.id), claims),
        refresh_token=create_refresh_token(str(user.id)),
        token_type="bearer",
        tenant_id=tenant_id,
        permissions=permissions,
    )

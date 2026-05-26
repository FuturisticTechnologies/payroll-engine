"""Idempotency support for create endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from fastapi import HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.idempotency import IdempotencyKey


@dataclass(frozen=True)
class IdempotencyReservation:
    record: IdempotencyKey


def _request_hash(request: Request, payload: BaseModel) -> str:
    canonical_payload = payload.model_dump_json(exclude_none=False)
    raw = f"{request.method}:{request.url.path}:{canonical_payload}".encode()
    return sha256(raw).hexdigest()


async def lookup_idempotency_key(
    db: AsyncSession,
    request: Request,
    payload: BaseModel,
    *,
    tenant_id: UUID | None,
) -> tuple[dict[str, Any] | None, IdempotencyReservation | None]:
    key = request.headers.get("Idempotency-Key")
    if key is None or key.strip() == "":
        return None, None
    key = key.strip()
    if len(key) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key must be 128 characters or fewer",
        )

    request_hash = _request_hash(request, payload)
    record = IdempotencyKey(
        key=key,
        method=request.method,
        path=request.url.path,
        request_hash=request_hash,
        status_code=0,
        response_body={},
        tenant_id=tenant_id,
    )
    try:
        async with db.begin_nested():
            db.add(record)
            await db.flush()
    except IntegrityError:
        existing = await _load_existing_record(db, request, key)
        if existing is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Idempotent request is still being finalised; retry shortly",
            ) from None
        return _validated_existing_response(existing, request_hash), None

    return None, IdempotencyReservation(record=record)


async def _load_existing_record(
    db: AsyncSession,
    request: Request,
    key: str,
) -> IdempotencyKey | None:
    result = await db.execute(
        select(IdempotencyKey).where(
            IdempotencyKey.key == key,
            IdempotencyKey.method == request.method,
            IdempotencyKey.path == request.url.path,
        )
    )
    return result.scalar_one_or_none()


def _validated_existing_response(
    existing: IdempotencyKey,
    request_hash: str,
) -> dict[str, Any]:
    if existing.request_hash != request_hash:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different payload",
        )
    if existing.status_code == 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotent request is still in progress; retry shortly",
        )
    return existing.response_body


def complete_idempotency_reservation(
    reservation: IdempotencyReservation,
    response_body: dict[str, Any],
    *,
    status_code: int,
) -> None:
    reservation.record.status_code = status_code
    reservation.record.response_body = response_body

"""Regression pack: who may read and run payroll over the API.

``test_rbac_matrix.py`` guards the catalog itself. This pack checks that the
endpoints actually enforce it, using real users with real tenant grants rather
than the seeded superuser, which bypasses every permission check.
"""
from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from app.core.database import AsyncSessionLocal, set_tenant_context
from app.core.payroll_framework import DEFAULT_TENANT_ID
from app.core.security import create_access_token
from app.models.rbac import Role, UserTenantRole
from app.models.user import User
from fastapi.testclient import TestClient
from sqlalchemy import select

PAY_RUNS = "/api/v1/pay-runs"

_VALID_PAY_RUN = {
    "tax_year": 2026,
    "period_number": 3,
    "pay_frequency": "monthly",
    "period_start": "2026-06-01",
    "period_end": "2026-06-30",
    "payment_date": "2026-06-30",
}


async def _create_user(role_code: str | None) -> UUID:
    """A non-superuser holding ``role_code`` in the default tenant, or no role."""
    async with AsyncSessionLocal() as session:
        await set_tenant_context(session, DEFAULT_TENANT_ID)
        user = User(
            email=f"rbac-{uuid4().hex[:10]}@example.com",
            full_name="RBAC Regression",
            # Never used: these tests mint a token rather than paying for a
            # bcrypt login per role.
            hashed_password="!",
            role="viewer",
            is_active=True,
            is_superuser=False,
        )
        session.add(user)
        await session.flush()
        if role_code is not None:
            role = (
                await session.execute(select(Role).where(Role.code == role_code))
            ).scalar_one()
            session.add(
                UserTenantRole(
                    user_id=user.id,
                    tenant_id=DEFAULT_TENANT_ID,
                    role_id=role.id,
                    is_active=True,
                )
            )
        await session.commit()
        return user.id


def _headers_for(client: TestClient, role_code: str | None) -> dict[str, str]:
    # Through the app's portal, so the engine's pooled connections stay on the
    # loop they were opened on (see test_local_database.py).
    user_id = client.portal.call(_create_user, role_code)
    token = create_access_token(str(user_id), {"tenant_id": str(DEFAULT_TENANT_ID)})
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(DEFAULT_TENANT_ID)}


@pytest.fixture(scope="module")
def headers_by_role(client: TestClient) -> dict[str, dict[str, str]]:
    return {
        role: _headers_for(client, None if role == "no_role" else role)
        for role in ("payroll_admin", "payroll_viewer", "employee_self_service", "no_role")
    }


# --- authentication ---------------------------------------------------------

# A fixed id, not uuid4(): parametrised ids must be identical on every xdist worker.
_SOME_RUN = "00000000-0000-4000-8000-00000000a310"
READ_PATHS = [
    pytest.param(PAY_RUNS, id="list"),
    pytest.param(f"{PAY_RUNS}/{_SOME_RUN}", id="detail"),
    pytest.param(f"{PAY_RUNS}/{_SOME_RUN}/ledger", id="ledger"),
]


@pytest.mark.parametrize("path", READ_PATHS)
def test_reads_without_a_token_are_unauthorised(client: TestClient, path: str) -> None:
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "authorization",
    ["Bearer not-a-jwt", "Bearer ", "Basic YWRtaW46YWRtaW4="],
    ids=["garbage-token", "empty-token", "basic-auth"],
)
def test_pay_run_with_an_unusable_credential_is_unauthorised(
    client: TestClient,
    authorization: str,
) -> None:
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN,
                           headers={"Authorization": authorization})
    assert response.status_code == 401, response.text


def test_pay_run_signed_with_a_foreign_key_is_unauthorised(client: TestClient) -> None:
    import jwt

    forged = jwt.encode(
        {"sub": str(uuid4()), "type": "access", "tenant_id": str(DEFAULT_TENANT_ID)},
        "not-the-server-secret-but-still-long-enough",
        algorithm="HS256",
    )
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN,
                           headers={"Authorization": f"Bearer {forged}"})
    assert response.status_code == 401


def test_refresh_token_cannot_be_used_to_run_payroll(client: TestClient) -> None:
    from app.core.security import create_refresh_token

    refresh = create_refresh_token(str(uuid4()))
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN,
                           headers={"Authorization": f"Bearer {refresh}"})
    assert response.status_code == 401


# --- authorisation ----------------------------------------------------------


@pytest.mark.parametrize("role", ["payroll_viewer", "employee_self_service", "no_role"])
def test_roles_without_payroll_run_cannot_create_a_pay_run(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
    role: str,
) -> None:
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN, headers=headers_by_role[role])
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied"


def test_permission_is_checked_before_the_body_is_validated(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
) -> None:
    """A caller who may not run payroll learns nothing about what a valid run is."""
    response = client.post(PAY_RUNS, json={"tax_year": "nonsense"},
                           headers=headers_by_role["payroll_viewer"])
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["employee_self_service", "no_role"])
@pytest.mark.parametrize("path", READ_PATHS)
def test_roles_without_payroll_read_cannot_see_pay_runs(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
    role: str,
    path: str,
) -> None:
    response = client.get(path, headers=headers_by_role[role])
    assert response.status_code == 403


@pytest.mark.parametrize("role", ["payroll_admin", "payroll_viewer"])
def test_roles_with_payroll_read_can_list_pay_runs(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
    role: str,
) -> None:
    response = client.get(f"{PAY_RUNS}?limit=1", headers=headers_by_role[role])
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_payroll_admin_passes_the_permission_check_for_creating_a_run(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
) -> None:
    # An invalid body proves the request got past RBAC without creating a run.
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN | {"period_number": 0},
                           headers=headers_by_role["payroll_admin"])
    assert response.status_code == 422


# --- tenant isolation -------------------------------------------------------


@pytest.mark.parametrize("role", ["payroll_admin", "payroll_viewer"])
def test_non_superuser_cannot_list_another_tenants_pay_runs(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
    role: str,
) -> None:
    response = client.get(f"{PAY_RUNS}?tenant_id={uuid4()}", headers=headers_by_role[role])
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied for requested tenant"


def test_non_superuser_cannot_run_payroll_for_another_tenant(
    client: TestClient,
    headers_by_role: dict[str, dict[str, str]],
) -> None:
    response = client.post(PAY_RUNS, json=_VALID_PAY_RUN | {"tenant_id": str(uuid4())},
                           headers=headers_by_role["payroll_admin"])
    assert response.status_code == 403
    assert response.json()["detail"] == "Permission denied for requested tenant"


def test_grant_in_one_tenant_does_not_carry_to_another(
    client: TestClient,
    auth_headers: dict[str, str],
    headers_by_role: dict[str, dict[str, str]],
) -> None:
    """Switching X-Tenant-ID to a tenant the user holds no role in removes every grant."""
    tenant = client.post(
        "/api/v1/tenants",
        json={
            "name": "RBAC Other Ltd",
            "legal_name": "RBAC Other Ltd",
            "slug": f"rbac-other-{uuid4().hex[:8]}",
        },
        headers=auth_headers,
    )
    assert tenant.status_code == 201, tenant.text
    other = headers_by_role["payroll_admin"] | {"X-Tenant-ID": tenant.json()["id"]}
    assert client.get(PAY_RUNS, headers=other).status_code == 403

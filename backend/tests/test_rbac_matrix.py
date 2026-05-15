"""RBAC catalog drift guard.

These are the assertions that catch a privilege mistake at commit time. They
run without a database on purpose — the catalog is seeded at boot, so by the
time a database could disagree the wrong grant already exists.
"""
from __future__ import annotations

from app.core.payroll_framework import ROLE_PERMISSION_CODES
from app.core.rbac_matrix import (
    ROLE_GRANTING_ROLES,
    WRITE_PERMISSIONS,
    build_matrix,
    catalog_drift,
    permission_codes,
    role_codes,
)


def test_catalog_has_no_drift() -> None:
    assert catalog_drift() == []


def test_every_role_resolves_to_a_grant() -> None:
    matrix = build_matrix()
    assert set(matrix) == set(role_codes())


def test_tenant_owner_holds_every_permission() -> None:
    matrix = build_matrix()
    assert matrix["tenant_owner"].permissions == set(permission_codes())


def test_viewer_and_self_service_are_read_only() -> None:
    matrix = build_matrix()
    assert matrix["payroll_viewer"].is_read_only
    assert matrix["employee_self_service"].is_read_only


def test_payroll_admin_can_run_payroll_but_not_manage_tenants() -> None:
    admin = build_matrix()["payroll_admin"]
    assert admin.allows("payroll:run")
    assert not admin.allows("tenants:manage")


def test_only_tenant_owner_can_grant_roles() -> None:
    granting = {
        code for code, grant in build_matrix().items() if grant.allows("rbac:manage")
    }
    assert granting == set(ROLE_GRANTING_ROLES)


def test_self_service_is_the_narrowest_role() -> None:
    matrix = build_matrix()
    self_service = matrix["employee_self_service"].permissions
    for code, grant in matrix.items():
        if code != "employee_self_service":
            assert self_service <= grant.permissions, f"{code} is narrower than self-service"


def test_write_permissions_are_all_declared() -> None:
    assert set(permission_codes()) >= WRITE_PERMISSIONS


def test_no_role_grants_a_permission_twice() -> None:
    for role, codes in ROLE_PERMISSION_CODES.items():
        assert len(codes) == len(set(codes)), role

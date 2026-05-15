"""Derived view of the role/permission catalog, plus a drift guard.

The catalog itself lives in :mod:`app.core.payroll_framework` as three
independent structures — ``SYSTEM_ROLES``, ``SYSTEM_PERMISSIONS`` and
``ROLE_PERMISSION_CODES``. Nothing in the application forces them to agree, and
they are seeded into the database at boot, so a typo becomes a *persisted*
grant rather than an error.

This module derives the matrix once and states the invariants explicitly, so a
mismatch is a failing test rather than a production privilege the client
discovers during a security review.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.payroll_framework import (
    ROLE_PERMISSION_CODES,
    SYSTEM_PERMISSIONS,
    SYSTEM_ROLES,
)

#: Permissions that let a caller change state rather than only read it.
WRITE_PERMISSIONS = frozenset(
    {
        "tenants:manage",
        "rbac:manage",
        "employees:write",
        "contracts:manage",
        "payroll:run",
    }
)

#: The only role permitted to grant roles to other users.
ROLE_GRANTING_ROLES = frozenset({"tenant_owner"})


@dataclass(frozen=True)
class RoleGrant:
    """One role and the permission codes it confers."""

    code: str
    name: str
    permissions: frozenset[str]

    @property
    def is_read_only(self) -> bool:
        return not (self.permissions & WRITE_PERMISSIONS)

    def allows(self, permission: str) -> bool:
        return permission in self.permissions


def role_codes() -> list[str]:
    """Declared role codes, in catalog order."""
    return [role["code"] for role in SYSTEM_ROLES]


def permission_codes() -> list[str]:
    """Declared permission codes, in catalog order."""
    return [permission["code"] for permission in SYSTEM_PERMISSIONS]


def build_matrix() -> dict[str, RoleGrant]:
    """Resolve the catalog into ``role code -> RoleGrant``."""
    names = {role["code"]: role["name"] for role in SYSTEM_ROLES}
    return {
        code: RoleGrant(
            code=code,
            name=names.get(code, code),
            permissions=frozenset(ROLE_PERMISSION_CODES.get(code, ())),
        )
        for code in role_codes()
    }


def catalog_drift() -> list[str]:
    """Return a human-readable list of catalog inconsistencies.

    Empty means the three structures agree. This is the function the drift test
    asserts on, and it is written to return *every* problem rather than raising
    on the first, so one run reports the whole picture.
    """
    problems: list[str] = []
    declared_roles = set(role_codes())
    declared_permissions = set(permission_codes())

    if len(role_codes()) != len(declared_roles):
        problems.append("SYSTEM_ROLES contains duplicate codes")
    if len(permission_codes()) != len(declared_permissions):
        problems.append("SYSTEM_PERMISSIONS contains duplicate codes")

    for role in sorted(set(ROLE_PERMISSION_CODES) - declared_roles):
        problems.append(f"ROLE_PERMISSION_CODES grants to undeclared role '{role}'")
    for role in sorted(declared_roles - set(ROLE_PERMISSION_CODES)):
        problems.append(f"role '{role}' is declared but granted no permissions")

    for role, codes in sorted(ROLE_PERMISSION_CODES.items()):
        for code in sorted(set(codes) - declared_permissions):
            problems.append(f"role '{role}' grants undeclared permission '{code}'")
        if len(codes) != len(set(codes)):
            problems.append(f"role '{role}' lists a permission more than once")

    granted = {code for codes in ROLE_PERMISSION_CODES.values() for code in codes}
    for code in sorted(declared_permissions - granted):
        problems.append(f"permission '{code}' is declared but granted to no role")

    return problems


def as_table() -> list[dict[str, object]]:
    """Flat, serialisable form for documentation and evidence export."""
    matrix = build_matrix()
    return [
        {
            "role": grant.code,
            "name": grant.name,
            "read_only": grant.is_read_only,
            "permissions": sorted(grant.permissions),
        }
        for grant in matrix.values()
    ]

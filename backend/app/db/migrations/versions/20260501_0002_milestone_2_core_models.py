"""Milestone 2 core models, tenancy, RBAC and security tables.

Revision ID: 20260501_0002
Revises: 20260410_0001
Create Date: 2026-05-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260501_0002"
down_revision: str | None = "20260410_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TENANT_ID = "00000000-0000-4000-8000-000000000001"

ROLE_IDS = {
    "tenant_owner": "00000000-0000-4000-8000-000000000101",
    "payroll_admin": "00000000-0000-4000-8000-000000000102",
    "payroll_viewer": "00000000-0000-4000-8000-000000000103",
    "employee_self_service": "00000000-0000-4000-8000-000000000104",
}

PERMISSION_IDS = {
    "tenants:manage": "00000000-0000-4000-8000-000000000201",
    "rbac:manage": "00000000-0000-4000-8000-000000000202",
    "employees:read": "00000000-0000-4000-8000-000000000203",
    "employees:write": "00000000-0000-4000-8000-000000000204",
    "contracts:manage": "00000000-0000-4000-8000-000000000205",
    "payroll:run": "00000000-0000-4000-8000-000000000206",
}

ROLE_PERMISSIONS = {
    "tenant_owner": [
        "tenants:manage",
        "rbac:manage",
        "employees:read",
        "employees:write",
        "contracts:manage",
        "payroll:run",
    ],
    "payroll_admin": [
        "employees:read",
        "employees:write",
        "contracts:manage",
        "payroll:run",
    ],
    "payroll_viewer": ["employees:read"],
    "employee_self_service": ["employees:read"],
}


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "btree_gist"')

    op.create_table(
        "tenants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=80), nullable=False),
        sa.Column("company_registration_number", sa.String(length=32), nullable=True),
        sa.Column("paye_reference", sa.String(length=32), nullable=True),
        sa.Column("accounts_office_reference", sa.String(length=32), nullable=True),
        sa.Column(
            "default_pay_frequency",
            sa.String(length=20),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("slug", name="uq_tenants_slug"),
    )
    op.create_index("ix_tenants_slug", "tenants", ["slug"])

    op.execute(
        sa.text(
            """
            INSERT INTO tenants (
                id, name, legal_name, slug, company_registration_number,
                paye_reference, accounts_office_reference, default_pay_frequency, status
            )
            VALUES (
                :id, 'Snovasys Futuristic Technologies', 'Snovasys Software Solutions Ltd',
                'snovasys-futuristic', NULL, '120/AB45678', '123PA00045678',
                'monthly', 'active'
            )
            ON CONFLICT (slug) DO NOTHING
            """
        ).bindparams(id=DEFAULT_TENANT_ID)
    )

    op.create_table(
        "roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_roles_code"),
    )
    op.create_index("ix_roles_code", "roles", ["code"])

    op.create_table(
        "permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
    )
    op.create_index("ix_permissions_code", "permissions", ["code"])

    for code, role_id in ROLE_IDS.items():
        name = code.replace("_", " ").title()
        op.execute(
            sa.text(
                """
                INSERT INTO roles (id, code, name, description, is_system)
                VALUES (:id, :code, :name, :description, true)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                id=role_id,
                code=code,
                name=name,
                description=f"System role for {name.lower()}.",
            )
        )

    permission_descriptions = {
        "tenants:manage": "Create and maintain employer tenants.",
        "rbac:manage": "Assign users to tenant roles.",
        "employees:read": "Read employee records.",
        "employees:write": "Create and update employee records.",
        "contracts:manage": "Maintain employment contracts and pay frequencies.",
        "payroll:run": "Execute payroll calculations and pay runs.",
    }
    for code, permission_id in PERMISSION_IDS.items():
        op.execute(
            sa.text(
                """
                INSERT INTO permissions (id, code, description)
                VALUES (:id, :code, :description)
                ON CONFLICT (code) DO NOTHING
                """
            ).bindparams(
                id=permission_id,
                code=code,
                description=permission_descriptions[code],
            )
        )

    op.create_table(
        "role_permissions",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permissions_pair"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index(
        "ix_role_permissions_permission_id",
        "role_permissions",
        ["permission_id"],
    )

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        for permission_code in permission_codes:
            op.execute(
                sa.text(
                    """
                    INSERT INTO role_permissions (role_id, permission_id)
                    VALUES (:role_id, :permission_id)
                    ON CONFLICT (role_id, permission_id) DO NOTHING
                    """
                ).bindparams(
                    role_id=ROLE_IDS[role_code],
                    permission_id=PERMISSION_IDS[permission_code],
                )
            )

    op.create_table(
        "user_tenant_roles",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "tenant_id", "role_id", name="uq_user_tenant_role"),
    )
    op.create_index("ix_user_tenant_roles_user_id", "user_tenant_roles", ["user_id"])
    op.create_index("ix_user_tenant_roles_tenant_id", "user_tenant_roles", ["tenant_id"])
    op.create_index("ix_user_tenant_roles_role_id", "user_tenant_roles", ["role_id"])

    op.execute(
        sa.text(
            """
            INSERT INTO user_tenant_roles (user_id, tenant_id, role_id)
            SELECT id, :tenant_id, :role_id
            FROM users
            WHERE role = 'super_admin' OR is_superuser = true
            ON CONFLICT (user_id, tenant_id, role_id) DO NOTHING
            """
        ).bindparams(tenant_id=DEFAULT_TENANT_ID, role_id=ROLE_IDS["tenant_owner"])
    )

    op.add_column(
        "employees",
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("employees", sa.Column("employee_number", sa.String(length=40), nullable=True))
    op.add_column(
        "employees",
        sa.Column("ni_category", sa.String(length=1), nullable=False, server_default="A"),
    )
    op.add_column(
        "employees",
        sa.Column(
            "employment_status",
            sa.String(length=20),
            nullable=False,
            server_default="active",
        ),
    )
    op.execute(
        sa.text(
            "UPDATE employees SET tenant_id = :tenant_id WHERE tenant_id IS NULL"
        ).bindparams(tenant_id=DEFAULT_TENANT_ID)
    )
    op.execute(
        """
        UPDATE employees
        SET employee_number = 'EMP-' || upper(left(replace(id::text, '-', ''), 8))
        WHERE employee_number IS NULL
        """
    )
    op.alter_column("employees", "tenant_id", nullable=False)
    op.alter_column("employees", "employee_number", nullable=False)
    op.create_foreign_key(
        "fk_employees_tenant_id_tenants",
        "employees",
        "tenants",
        ["tenant_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_employees_tenant_id", "employees", ["tenant_id"])
    op.create_index("ix_employees_employee_number", "employees", ["employee_number"])
    op.drop_constraint("uq_employees_email", "employees", type_="unique")
    op.drop_constraint("uq_employees_ni_number", "employees", type_="unique")
    op.create_unique_constraint(
        "uq_employees_tenant_email",
        "employees",
        ["tenant_id", "email"],
    )
    op.create_unique_constraint(
        "uq_employees_tenant_ni_number",
        "employees",
        ["tenant_id", "national_insurance_number"],
    )
    op.create_unique_constraint(
        "uq_employees_tenant_employee_number",
        "employees",
        ["tenant_id", "employee_number"],
    )

    op.create_table(
        "employment_contracts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "contract_type",
            sa.String(length=32),
            nullable=False,
            server_default="permanent",
        ),
        sa.Column(
            "pay_frequency",
            sa.String(length=20),
            nullable=False,
            server_default="monthly",
        ),
        sa.Column("annual_salary", sa.Numeric(14, 2), nullable=True),
        sa.Column("weekly_hours", sa.Numeric(5, 2), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "employee_id",
            "effective_from",
            name="uq_employment_contracts_employee_effective_from",
        ),
    )
    op.create_index("ix_employment_contracts_tenant_id", "employment_contracts", ["tenant_id"])
    op.create_index(
        "ix_employment_contracts_employee_id",
        "employment_contracts",
        ["employee_id"],
    )
    op.create_index(
        "uq_employment_contracts_employee_primary",
        "employment_contracts",
        ["employee_id"],
        unique=True,
        postgresql_where=sa.text("is_primary"),
    )
    op.execute(
        """
        ALTER TABLE employment_contracts
        ADD CONSTRAINT ex_employment_contracts_no_overlap
        EXCLUDE USING gist (
            employee_id WITH =,
            daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[]') WITH &&
        )
        """
    )

    op.create_table(
        "idempotency_keys",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=False),
        sa.Column("path", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False, server_default="201"),
        sa.Column("response_body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("key", "method", "path", name="uq_idempotency_key_route"),
    )
    op.create_index("ix_idempotency_keys_key", "idempotency_keys", ["key"])
    op.create_index("ix_idempotency_keys_tenant_id", "idempotency_keys", ["tenant_id"])

    _enable_tenant_rls("tenants", _tenant_identity_policy(), _tenant_identity_policy())
    _enable_tenant_rls("employees", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("employment_contracts", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("user_tenant_roles", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("idempotency_keys", _tenant_policy(), _tenant_policy())


def downgrade() -> None:
    for table in [
        "idempotency_keys",
        "user_tenant_roles",
        "employment_contracts",
        "employees",
        "tenants",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index("ix_idempotency_keys_tenant_id", table_name="idempotency_keys")
    op.drop_index("ix_idempotency_keys_key", table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.execute(
        "ALTER TABLE employment_contracts "
        "DROP CONSTRAINT IF EXISTS ex_employment_contracts_no_overlap"
    )
    op.drop_index(
        "uq_employment_contracts_employee_primary",
        table_name="employment_contracts",
    )
    op.drop_index("ix_employment_contracts_employee_id", table_name="employment_contracts")
    op.drop_index("ix_employment_contracts_tenant_id", table_name="employment_contracts")
    op.drop_table("employment_contracts")

    op.drop_constraint("uq_employees_tenant_employee_number", "employees", type_="unique")
    op.drop_constraint("uq_employees_tenant_ni_number", "employees", type_="unique")
    op.drop_constraint("uq_employees_tenant_email", "employees", type_="unique")
    op.drop_index("ix_employees_employee_number", table_name="employees")
    op.drop_index("ix_employees_tenant_id", table_name="employees")
    op.drop_constraint("fk_employees_tenant_id_tenants", "employees", type_="foreignkey")
    op.drop_column("employees", "employment_status")
    op.drop_column("employees", "ni_category")
    op.drop_column("employees", "employee_number")
    op.drop_column("employees", "tenant_id")
    op.create_unique_constraint("uq_employees_email", "employees", ["email"])
    op.create_unique_constraint(
        "uq_employees_ni_number",
        "employees",
        ["national_insurance_number"],
    )

    op.drop_index("ix_user_tenant_roles_role_id", table_name="user_tenant_roles")
    op.drop_index("ix_user_tenant_roles_tenant_id", table_name="user_tenant_roles")
    op.drop_index("ix_user_tenant_roles_user_id", table_name="user_tenant_roles")
    op.drop_table("user_tenant_roles")

    op.drop_index("ix_role_permissions_permission_id", table_name="role_permissions")
    op.drop_index("ix_role_permissions_role_id", table_name="role_permissions")
    op.drop_table("role_permissions")

    op.drop_index("ix_permissions_code", table_name="permissions")
    op.drop_table("permissions")

    op.drop_index("ix_roles_code", table_name="roles")
    op.drop_table("roles")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_table("tenants")


def _tenant_policy() -> str:
    return _superuser_or(
        "current_setting('app.tenant_id', true) <> '' "
        "AND tenant_id::text = current_setting('app.tenant_id', true)"
    )


def _tenant_identity_policy() -> str:
    return _superuser_or(
        "current_setting('app.tenant_id', true) <> '' "
        "AND id::text = current_setting('app.tenant_id', true)"
    )


def _superuser_or(predicate: str) -> str:
    return f"current_setting('app.is_superuser', true) = 'true' OR ({predicate})"


def _enable_tenant_rls(table: str, using_clause: str, check_clause: str) -> None:
    op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table}_tenant_isolation ON {table}
        USING ({using_clause})
        WITH CHECK ({check_clause})
        """
    )

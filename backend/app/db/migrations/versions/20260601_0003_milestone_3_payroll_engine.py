"""Milestone 3 payroll engine, pay runs and immutable ledger.

Revision ID: 20260601_0003
Revises: 20260501_0002
Create Date: 2026-06-01
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260601_0003"
down_revision: str | None = "20260501_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PAYROLL_READ_PERMISSION_ID = "00000000-0000-4000-8000-000000000207"
ROLE_IDS = {
    "tenant_owner": "00000000-0000-4000-8000-000000000101",
    "payroll_admin": "00000000-0000-4000-8000-000000000102",
    "payroll_viewer": "00000000-0000-4000-8000-000000000103",
}


def upgrade() -> None:
    _seed_payroll_read_permission()

    op.create_table(
        "pay_periods",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("period_number", sa.Integer(), nullable=False),
        sa.Column("pay_frequency", sa.String(length=20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="open"),
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
        sa.UniqueConstraint(
            "tenant_id",
            "tax_year",
            "pay_frequency",
            "period_number",
            name="uq_pay_periods_tenant_cycle",
        ),
    )
    op.create_index("ix_pay_periods_tenant_id", "pay_periods", ["tenant_id"])

    op.create_table(
        "pay_runs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_period_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="calculated",
        ),
        sa.Column("employee_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "gross_earnings",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column(
            "total_deductions",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
        sa.Column(
            "calculation_version",
            sa.String(length=40),
            nullable=False,
            server_default="m3-basic-v1",
        ),
        sa.Column(
            "calculated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("ledger_entry_hash", sa.String(length=64), nullable=True),
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
        sa.ForeignKeyConstraint(["pay_period_id"], ["pay_periods.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "tenant_id",
            "pay_period_id",
            name="uq_pay_runs_tenant_pay_period",
        ),
    )
    op.create_index("ix_pay_runs_tenant_id", "pay_runs", ["tenant_id"])
    op.create_index("ix_pay_runs_pay_period_id", "pay_runs", ["pay_period_id"])
    op.create_index("ix_pay_runs_created_by_user_id", "pay_runs", ["created_by_user_id"])

    op.create_table(
        "payroll_run_lines",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_number", sa.String(length=40), nullable=False),
        sa.Column("employee_name", sa.String(length=220), nullable=False),
        sa.Column("base_salary", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "additional_earnings",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("gross_pay", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column(
            "total_deductions",
            sa.Numeric(14, 2),
            nullable=False,
            server_default="0.00",
        ),
        sa.Column("net_pay", sa.Numeric(14, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="GBP"),
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
        sa.ForeignKeyConstraint(["pay_run_id"], ["pay_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contract_id"], ["employment_contracts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "pay_run_id",
            "employee_id",
            name="uq_payroll_run_lines_run_employee",
        ),
    )
    op.create_index("ix_payroll_run_lines_tenant_id", "payroll_run_lines", ["tenant_id"])
    op.create_index("ix_payroll_run_lines_pay_run_id", "payroll_run_lines", ["pay_run_id"])
    op.create_index("ix_payroll_run_lines_employee_id", "payroll_run_lines", ["employee_id"])
    op.create_index("ix_payroll_run_lines_contract_id", "payroll_run_lines", ["contract_id"])

    op.create_table(
        "payroll_line_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_run_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("taxable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("pensionable", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("source", sa.String(length=40), nullable=False, server_default="manual"),
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
        sa.ForeignKeyConstraint(["pay_run_id"], ["pay_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["pay_run_line_id"],
            ["payroll_run_lines.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_payroll_line_items_tenant_id", "payroll_line_items", ["tenant_id"])
    op.create_index("ix_payroll_line_items_pay_run_id", "payroll_line_items", ["pay_run_id"])
    op.create_index(
        "ix_payroll_line_items_pay_run_line_id",
        "payroll_line_items",
        ["pay_run_line_id"],
    )
    op.create_index("ix_payroll_line_items_employee_id", "payroll_line_items", ["employee_id"])

    op.create_table(
        "payroll_ledger_entries",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("pay_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("entry_type", sa.String(length=60), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("previous_hash", sa.String(length=64), nullable=True),
        sa.Column("entry_hash", sa.String(length=64), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pay_run_id"], ["pay_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint(
            "tenant_id",
            "sequence_number",
            name="uq_payroll_ledger_entries_tenant_sequence",
        ),
        sa.UniqueConstraint("entry_hash", name="uq_payroll_ledger_entries_hash"),
    )
    op.create_index(
        "ix_payroll_ledger_entries_tenant_id",
        "payroll_ledger_entries",
        ["tenant_id"],
    )
    op.create_index(
        "ix_payroll_ledger_entries_pay_run_id",
        "payroll_ledger_entries",
        ["pay_run_id"],
    )
    op.create_index(
        "ix_payroll_ledger_entries_created_by_user_id",
        "payroll_ledger_entries",
        ["created_by_user_id"],
    )

    _enable_tenant_rls("pay_periods", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("pay_runs", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("payroll_run_lines", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("payroll_line_items", _tenant_policy(), _tenant_policy())
    _enable_tenant_rls("payroll_ledger_entries", _tenant_policy(), _tenant_policy())
    _create_append_only_ledger_trigger()


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_payroll_ledger_entries_immutable "
        "ON payroll_ledger_entries"
    )
    op.execute("DROP FUNCTION IF EXISTS prevent_payroll_ledger_mutation()")

    for table in [
        "payroll_ledger_entries",
        "payroll_line_items",
        "payroll_run_lines",
        "pay_runs",
        "pay_periods",
    ]:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")

    op.drop_index(
        "ix_payroll_ledger_entries_created_by_user_id",
        table_name="payroll_ledger_entries",
    )
    op.drop_index("ix_payroll_ledger_entries_pay_run_id", table_name="payroll_ledger_entries")
    op.drop_index("ix_payroll_ledger_entries_tenant_id", table_name="payroll_ledger_entries")
    op.drop_table("payroll_ledger_entries")

    op.drop_index("ix_payroll_line_items_employee_id", table_name="payroll_line_items")
    op.drop_index("ix_payroll_line_items_pay_run_line_id", table_name="payroll_line_items")
    op.drop_index("ix_payroll_line_items_pay_run_id", table_name="payroll_line_items")
    op.drop_index("ix_payroll_line_items_tenant_id", table_name="payroll_line_items")
    op.drop_table("payroll_line_items")

    op.drop_index("ix_payroll_run_lines_contract_id", table_name="payroll_run_lines")
    op.drop_index("ix_payroll_run_lines_employee_id", table_name="payroll_run_lines")
    op.drop_index("ix_payroll_run_lines_pay_run_id", table_name="payroll_run_lines")
    op.drop_index("ix_payroll_run_lines_tenant_id", table_name="payroll_run_lines")
    op.drop_table("payroll_run_lines")

    op.drop_index("ix_pay_runs_created_by_user_id", table_name="pay_runs")
    op.drop_index("ix_pay_runs_pay_period_id", table_name="pay_runs")
    op.drop_index("ix_pay_runs_tenant_id", table_name="pay_runs")
    op.drop_table("pay_runs")

    op.drop_index("ix_pay_periods_tenant_id", table_name="pay_periods")
    op.drop_table("pay_periods")

    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id = :permission_id
            """
        ).bindparams(permission_id=PAYROLL_READ_PERMISSION_ID)
    )
    op.execute(
        sa.text("DELETE FROM permissions WHERE id = :permission_id").bindparams(
            permission_id=PAYROLL_READ_PERMISSION_ID
        )
    )


def _seed_payroll_read_permission() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description)
            VALUES (
                :permission_id,
                'payroll:read',
                'Read payroll periods, runs and ledger evidence.'
            )
            ON CONFLICT (code) DO NOTHING
            """
        ).bindparams(permission_id=PAYROLL_READ_PERMISSION_ID)
    )
    for role_id in ROLE_IDS.values():
        op.execute(
            sa.text(
                """
                INSERT INTO role_permissions (role_id, permission_id)
                VALUES (:role_id, :permission_id)
                ON CONFLICT (role_id, permission_id) DO NOTHING
                """
            ).bindparams(role_id=role_id, permission_id=PAYROLL_READ_PERMISSION_ID)
        )


def _tenant_policy() -> str:
    return _superuser_or(
        "current_setting('app.tenant_id', true) <> '' "
        "AND tenant_id::text = current_setting('app.tenant_id', true)"
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


def _create_append_only_ledger_trigger() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_payroll_ledger_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'payroll ledger entries are append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_payroll_ledger_entries_immutable
        BEFORE UPDATE OR DELETE ON payroll_ledger_entries
        FOR EACH ROW EXECUTE FUNCTION prevent_payroll_ledger_mutation()
        """
    )

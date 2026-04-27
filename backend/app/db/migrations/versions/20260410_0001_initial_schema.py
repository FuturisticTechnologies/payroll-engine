"""Initial schema — users, employees, audit_logs.

Milestone 1 baseline. Pay-bearing tables (salary structures, payslips, tax
period registers, pension schemes) arrive in subsequent migrations.

Revision ID: 20260410_0001
Revises:
Create Date: 2026-04-10
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260410_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extensions are created by infra/postgres/init.sql on first boot;
    # include idempotent guards here too so the migration is self-contained.
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "citext"')

    # -------------------- users --------------------
    op.create_table(
        "users",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="viewer",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    # -------------------- employees --------------------
    op.create_table(
        "employees",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("first_name", sa.String(length=100), nullable=False),
        sa.Column("last_name", sa.String(length=100), nullable=False),
        sa.Column("email", postgresql.CITEXT(), nullable=False),
        sa.Column(
            "national_insurance_number",
            sa.String(length=9),
            nullable=False,
        ),
        sa.Column(
            "tax_code",
            sa.String(length=10),
            nullable=False,
            server_default="1257L",
        ),
        sa.Column("employment_start_date", sa.Date(), nullable=False),
        sa.Column("job_title", sa.String(length=150), nullable=True),
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
        sa.UniqueConstraint("email", name="uq_employees_email"),
        sa.UniqueConstraint(
            "national_insurance_number", name="uq_employees_ni_number"
        ),
    )
    op.create_index("ix_employees_email", "employees", ["email"])
    op.create_index(
        "ix_employees_ni_number",
        "employees",
        ["national_insurance_number"],
    )

    # -------------------- audit_logs --------------------
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("actor_ip", sa.String(length=45), nullable=True),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=100), nullable=False),
        sa.Column("entity_id", sa.String(length=100), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
    )
    op.create_index("ix_audit_logs_occurred_at", "audit_logs", ["occurred_at"])
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_event_type", "audit_logs", ["event_type"])
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_event_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_occurred_at", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_employees_ni_number", table_name="employees")
    op.drop_index("ix_employees_email", table_name="employees")
    op.drop_table("employees")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

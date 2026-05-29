"""SQLAlchemy ORM models.

Import every model here so Alembic's autogenerate picks them up via the
shared ``Base.metadata``.
"""
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.base import Base  # noqa: F401
from app.models.employee import Employee  # noqa: F401
from app.models.employment import EmploymentContract  # noqa: F401
from app.models.idempotency import IdempotencyKey  # noqa: F401
from app.models.rbac import Permission, Role, RolePermission, UserTenantRole  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401

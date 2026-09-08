"""OpenAPI document metadata.

Kept out of main.py so a service's public identity - its title, what each tag
means, the auth note a caller reads before their first request - is edited in
one obvious place instead of inside the FastAPI construction call.

Every milestone repo builds the same product at a different point in its life,
so the title names the milestone. Left generic, five deployments all called
"PayrollFuturistic API" are indistinguishable in a browser tab.
"""
from __future__ import annotations

from typing import Any

#: Milestone 3 - Basic Payroll Engine
SERVICE_TITLE = "PayrollFuturistic API - Payroll Engine"

SERVICE_SUMMARY = "Milestone 3: Basic Payroll Engine."

SERVICE_DESCRIPTION = """\
UK-compliant payroll SaaS platform: HMRC (PAYE, NI, RTI), statutory payments,
pension auto-enrolment and UK GDPR.

**Authentication.** Call `POST /api/v1/auth/login`, then send the access token
as `Authorization: Bearer <token>`. Use the **Authorize** button above to apply
it to every request on this page. The same token is accepted by the HMRC RTI
Service and the Integration Hub.

**Tenancy.** The tenant comes from the token's `tenant_id` claim and can be
overridden with an `X-Tenant-ID` header. Postgres row-level security enforces
the boundary, so a token cannot read another tenant's rows.

**Correlation.** Every response carries `X-Request-ID`, echoed from the request
when you supply one. Quote it in any bug report.
"""

CONTACT: dict[str, Any] = {
    "name": "Futuristic Technologies",
    "url": "https://github.com/FuturisticTechnologies",
}

LICENSE: dict[str, Any] = {
    "name": "Proprietary - Futuristic Technologies",
}

#: Relative, so "Try it out" targets whichever host served the page. An absolute
#: URL would send requests from the Azure deployment back to localhost.
SERVERS: list[dict[str, Any]] = [
    {"url": "/", "description": "This deployment."},
]

#: Ordered to match app/api/v1/router.py, which is the order the UI renders.
OPENAPI_TAGS: list[dict[str, Any]] = [
    {
        "name": "health",
        "description": (
            "Liveness and readiness probes. Unauthenticated; readiness returns 503 "
            "when Postgres is unreachable."
        ),
    },
    {
        "name": "meta",
        "description": (
            "Build version and the SOW milestone this deployment corresponds to."
        ),
    },
    {
        "name": "auth",
        "description": (
            "CSRF token issue and login. The access token returned here is also "
            "accepted by the .NET services."
        ),
    },
    {
        "name": "tenants",
        "description": (
            "Tenant records. Every other resource in this API is scoped to exactly "
            "one tenant."
        ),
    },
    {"name": "employees", "description": "Employee master records."},
    {
        "name": "employment-contracts",
        "description": (
            "Contracts held against an employee: terms, pay basis and effective "
            "dates."
        ),
    },
    {
        "name": "pay-runs",
        "description": (
            "Pay run lifecycle and the ledger each committed run produces."
        ),
    },
    {
        "name": "framework",
        "description": (
            "Read-only reference catalogue the calculations resolve against: pay "
            "elements, schedules and rates."
        ),
    },
]

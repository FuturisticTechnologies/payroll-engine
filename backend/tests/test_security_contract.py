"""Security response-header contract.

M2-08 added the header set and the CSRF bootstrap. These assertions pin the
contract at the function level rather than through the HTTP stack, so they keep
running when the database is unavailable and they fail on the specific header
that regressed instead of on a whole request.
"""
from __future__ import annotations

from app.main import (
    _CSRF_EXEMPT_PATHS,
    _UNSAFE_METHODS,
    _apply_security_headers,
    _csrf_failed_response,
)
from starlette.responses import JSONResponse, Response


def _headers() -> dict[str, str]:
    response = Response()
    _apply_security_headers(response)
    return dict(response.headers)


def test_clickjacking_and_sniffing_are_denied() -> None:
    headers = _headers()
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"


def test_referrer_and_isolation_policies_are_set() -> None:
    headers = _headers()
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["cross-origin-opener-policy"] == "same-origin"


def test_permissions_policy_disables_device_access() -> None:
    policy = _headers()["permissions-policy"]
    for feature in ("camera=()", "microphone=()", "geolocation=()"):
        assert feature in policy


def test_csp_forbids_framing_and_pins_base_uri() -> None:
    csp = _headers()["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    assert "default-src 'self'" in csp


def test_csp_does_not_allow_wildcard_sources() -> None:
    assert "*" not in _headers()["content-security-policy"]


def test_existing_header_values_are_not_overwritten() -> None:
    response = Response()
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    _apply_security_headers(response)
    # setdefault semantics: a deliberate per-route override must survive.
    assert response.headers["x-frame-options"] == "SAMEORIGIN"


def test_csrf_protection_covers_every_state_changing_method() -> None:
    assert sorted(_UNSAFE_METHODS) == ["DELETE", "PATCH", "POST", "PUT"]


def test_csrf_exemptions_are_limited_to_bootstrap_endpoints() -> None:
    assert sorted(_CSRF_EXEMPT_PATHS) == [
        "/api/v1/auth/csrf",
        "/api/v1/auth/login",
    ]


def test_csrf_failure_is_403_and_still_carries_security_headers() -> None:
    response = _csrf_failed_response("req-1")
    assert isinstance(response, JSONResponse)
    assert response.status_code == 403
    assert response.headers["x-request-id"] == "req-1"
    assert response.headers["x-content-type-options"] == "nosniff"

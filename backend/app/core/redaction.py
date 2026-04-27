"""Redaction helpers for structured log events.

UK GDPR requires that payroll identifiers do not leak into application logs.
Log sinks are retained for operational debugging and are not part of the
7-year payroll audit record, so anything personally identifying is masked
before it reaches structlog rather than being scrubbed downstream.

Masking is deliberately lossy but *stable*: the same input always produces the
same mask, so a support engineer can still correlate two log lines about the
same employee without the log ever holding the identifier itself.
"""
from __future__ import annotations

import re
from typing import Any

REDACTED = "[redacted]"

#: Keys whose values are always masked regardless of their content.
SENSITIVE_KEYS = frozenset(
    {
        "access_token",
        "account_number",
        "authorization",
        "bank_account",
        "date_of_birth",
        "email",
        "national_insurance_number",
        "nino",
        "password",
        "refresh_token",
        "secret",
        "sort_code",
        "x-csrf-token",
    }
)

# Deliberately more permissive than the HMRC prefix rule, which excludes
# D, F, I, O, Q, U and V. A redaction net should over-mask rather than
# under-mask, and the strict charset misses HMRC's own QQ123456C placeholder,
# which is exactly the value that turns up pasted into support tickets.
_NINO_RE = re.compile(
    r"\b([A-Z]{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?([A-D])\b",
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_SORT_CODE_RE = re.compile(r"\b\d{2}-\d{2}-\d{2}\b")
_ACCOUNT_RE = re.compile(r"\b\d{8}\b")

_MAX_DEPTH = 6


def mask_nino(value: str) -> str:
    """Mask a National Insurance number, keeping only its two-letter prefix."""
    return _NINO_RE.sub(lambda m: f"{m.group(1).upper()}******{m.group(5).upper()}", value)


def mask_email(value: str) -> str:
    """Mask the local part of an email address, keeping the domain."""

    def _sub(match: re.Match[str]) -> str:
        local, _, domain = match.group(0).partition("@")
        return f"{local[0]}***@{domain}" if local else f"***@{domain}"

    return _EMAIL_RE.sub(_sub, value)


def mask_bank_details(value: str) -> str:
    """Mask sort codes and eight-digit account numbers."""
    value = _SORT_CODE_RE.sub("**-**-**", value)
    return _ACCOUNT_RE.sub("********", value)


def redact_text(value: str) -> str:
    """Apply every text-level mask to a free-form string."""
    return mask_bank_details(mask_email(mask_nino(value)))


def redact_event(event: Any, _depth: int = 0) -> Any:
    """Recursively redact a structlog event dict.

    Sensitive keys are replaced wholesale; every other string is passed through
    the pattern masks so identifiers embedded in messages are caught too.
    Recursion is depth-capped so a cyclic or pathologically nested payload
    cannot stall the logging path.
    """
    if _depth >= _MAX_DEPTH:
        return REDACTED

    if isinstance(event, dict):
        return {
            key: REDACTED
            if str(key).lower() in SENSITIVE_KEYS
            else redact_event(value, _depth + 1)
            for key, value in event.items()
        }
    if isinstance(event, list):
        return [redact_event(item, _depth + 1) for item in event]
    if isinstance(event, tuple):
        return tuple(redact_event(item, _depth + 1) for item in event)
    if isinstance(event, str):
        return redact_text(event)
    return event


def redaction_processor(
    _logger: object,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor entry point.

    Kept as a thin adapter so :func:`redact_event` stays independently testable
    without constructing a logger.
    """
    result = redact_event(event_dict)
    return result if isinstance(result, dict) else {"event": REDACTED}

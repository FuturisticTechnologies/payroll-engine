"""Log redaction unit tests.

Deliberately free of the ``client`` fixture: these exercise pure functions and
must stay runnable on a machine with no database, which is the state the M1
scaffold is normally developed against.
"""
from __future__ import annotations

from app.core.redaction import (
    REDACTED,
    mask_bank_details,
    mask_email,
    mask_nino,
    redact_event,
    redact_text,
    redaction_processor,
)


def test_nino_keeps_prefix_and_suffix_only() -> None:
    assert mask_nino("QQ123456C") == "QQ******C"


def test_nino_matches_spaced_format() -> None:
    assert mask_nino("QQ 12 34 56 C") == "QQ******C"


def test_nino_is_case_normalised() -> None:
    assert mask_nino("qq123456c") == "QQ******C"


def test_non_nino_text_is_untouched() -> None:
    assert mask_nino("employee 12345678") == "employee 12345678"


def test_email_keeps_domain_for_support_triage() -> None:
    assert mask_email("payroll.admin@example.co.uk") == "p***@example.co.uk"


def test_sort_code_and_account_number_are_masked() -> None:
    masked = mask_bank_details("sort 20-30-40 account 12345678")
    assert masked == "sort **-**-** account ********"


def test_redact_text_applies_every_mask() -> None:
    masked = redact_text("QQ123456C paid to a@b.co.uk via 20-30-40")
    assert "QQ123456C" not in masked
    assert "a@b.co.uk" not in masked
    assert "20-30-40" not in masked


def test_sensitive_keys_are_dropped_wholesale() -> None:
    event = redact_event({"password": "hunter2", "nino": "QQ123456C"})
    assert event == {"password": REDACTED, "nino": REDACTED}


def test_sensitive_key_match_is_case_insensitive() -> None:
    assert redact_event({"Authorization": "Bearer abc"}) == {"Authorization": REDACTED}


def test_nested_structures_are_walked() -> None:
    event = redact_event({"employees": [{"note": "ref QQ123456C"}]})
    assert event["employees"][0]["note"] == "ref QQ******C"


def test_tuples_keep_their_type() -> None:
    assert redact_event(("QQ123456C",)) == ("QQ******C",)


def test_non_string_scalars_pass_through_unchanged() -> None:
    assert redact_event({"count": 3, "gross": None, "ok": True}) == {
        "count": 3,
        "gross": None,
        "ok": True,
    }


def test_depth_cap_stops_runaway_nesting() -> None:
    deep: dict[str, object] = {"level": "QQ123456C"}
    for _ in range(12):
        deep = {"child": deep}
    # Must terminate and must not raise.
    assert redact_event(deep) is not None


def test_processor_returns_a_dict_for_structlog() -> None:
    result = redaction_processor(None, "info", {"event": "login", "email": "a@b.com"})
    assert result["event"] == "login"
    assert result["email"] == REDACTED

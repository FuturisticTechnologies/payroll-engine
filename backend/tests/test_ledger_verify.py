"""Ledger hash-chain verification, including the tamper demonstration.

The chain is only worth having if a modified row is detectable, so most of
these tests break something on purpose and assert that the break is found and
correctly described.
"""
from __future__ import annotations

from typing import Any

from app.core.ledger_verify import (
    ChainVerdict,
    LedgerEntryView,
    entry_hash,
    payload_hash,
    verify_chain,
    verify_rows,
)


def _entry(
    sequence_number: int,
    payload: dict[str, Any],
    previous_hash: str | None,
    entry_type: str = "pay_run_calculated",
) -> LedgerEntryView:
    """Build a correctly-linked entry the way the engine writes one."""
    digest = payload_hash(payload)
    return LedgerEntryView(
        sequence_number=sequence_number,
        entry_type=entry_type,
        payload_hash=digest,
        entry_hash=entry_hash(previous_hash, digest, sequence_number, entry_type),
        payload=payload,
        previous_hash=previous_hash,
    )


def _chain(length: int) -> list[LedgerEntryView]:
    entries: list[LedgerEntryView] = []
    previous: str | None = None
    for index in range(1, length + 1):
        entry = _entry(index, {"run": index, "net_pay": f"{index}000.00"}, previous)
        entries.append(entry)
        previous = entry.entry_hash
    return entries


# --------------------------------------------------------------- intact chains

def test_empty_ledger_is_trivially_intact() -> None:
    verdict = verify_chain([])
    assert verdict.is_intact
    assert verdict.entries_checked == 0


def test_single_entry_chain_is_intact() -> None:
    assert verify_chain(_chain(1)).is_intact


def test_long_chain_is_intact() -> None:
    verdict = verify_chain(_chain(25))
    assert verdict.is_intact
    assert verdict.entries_checked == 25


def test_entries_may_arrive_out_of_order() -> None:
    entries = _chain(5)
    assert verify_chain(list(reversed(entries))).is_intact


def test_canonical_hash_matches_the_engine_construction() -> None:
    # Restates the engine's rule literally. If this fails, the writer and the
    # verifier have diverged and one of them is wrong.
    import json
    from hashlib import sha256

    payload = {"b": 2, "a": 1}
    expected_payload = sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    assert payload_hash(payload) == expected_payload

    expected_entry = sha256(
        f"{''}:{expected_payload}:1:pay_run_calculated".encode()
    ).hexdigest()
    assert entry_hash(None, expected_payload, 1, "pay_run_calculated") == expected_entry


def test_key_order_does_not_change_the_hash() -> None:
    assert payload_hash({"a": 1, "b": 2}) == payload_hash({"b": 2, "a": 1})


# ------------------------------------------------------------- tamper detection

def test_altering_a_payload_is_detected() -> None:
    entries = _chain(3)
    tampered = entries[1]
    entries[1] = LedgerEntryView(
        sequence_number=tampered.sequence_number,
        entry_type=tampered.entry_type,
        payload_hash=tampered.payload_hash,
        entry_hash=tampered.entry_hash,
        payload={"run": 2, "net_pay": "9999.00"},  # the only change
        previous_hash=tampered.previous_hash,
    )
    verdict = verify_chain(entries)
    assert not verdict.is_intact
    assert any("payload was altered" in problem for problem in verdict.problems)


def test_recomputing_the_payload_hash_still_fails_the_chain() -> None:
    # The realistic attack: change the payload *and* fix its hash. The entry
    # hash and every downstream link still give it away.
    entries = _chain(3)
    forged_payload = {"run": 2, "net_pay": "9999.00"}
    entries[1] = LedgerEntryView(
        sequence_number=2,
        entry_type="pay_run_calculated",
        payload_hash=payload_hash(forged_payload),
        entry_hash=entries[1].entry_hash,
        payload=forged_payload,
        previous_hash=entries[1].previous_hash,
    )
    verdict = verify_chain(entries)
    assert not verdict.is_intact
    assert any("entry_hash does not match" in problem for problem in verdict.problems)


def test_rewriting_an_entry_completely_breaks_the_following_link() -> None:
    # Change the payload, fix the payload hash, fix the entry hash. The entry
    # is now internally consistent — but entry 3 still points at the old hash.
    entries = _chain(3)
    forged_payload = {"run": 2, "net_pay": "9999.00"}
    entries[1] = _entry(2, forged_payload, entries[1].previous_hash)
    verdict = verify_chain(entries)
    assert not verdict.is_intact
    assert any("previous_hash does not match" in problem for problem in verdict.problems)


def test_deleting_an_entry_is_detected_as_a_gap() -> None:
    entries = _chain(4)
    del entries[2]
    verdict = verify_chain(entries)
    assert not verdict.is_intact
    assert any("gap or a duplicate" in problem for problem in verdict.problems)


def test_a_genesis_entry_claiming_a_predecessor_is_rejected() -> None:
    entries = _chain(1)
    entries[0] = LedgerEntryView(
        sequence_number=1,
        entry_type=entries[0].entry_type,
        payload_hash=entries[0].payload_hash,
        entry_hash=entries[0].entry_hash,
        payload=entries[0].payload,
        previous_hash="a" * 64,
    )
    assert not verify_chain(entries).is_intact


def test_changing_the_entry_type_invalidates_the_hash() -> None:
    entries = _chain(1)
    entries[0] = LedgerEntryView(
        sequence_number=1,
        entry_type="pay_run_reversed",
        payload_hash=entries[0].payload_hash,
        entry_hash=entries[0].entry_hash,
        payload=entries[0].payload,
        previous_hash=None,
    )
    assert not verify_chain(entries).is_intact


# ------------------------------------------------------------------- reporting

def test_verdict_reports_every_problem_not_just_the_first() -> None:
    entries = _chain(4)
    entries[1] = LedgerEntryView(
        sequence_number=2,
        entry_type="pay_run_calculated",
        payload_hash="0" * 64,
        entry_hash="1" * 64,
        payload={"run": 2},
        previous_hash=None,
    )
    verdict = verify_chain(entries)
    assert len(verdict.problems) >= 3


def test_verdict_str_is_human_readable() -> None:
    assert "intact" in str(verify_chain(_chain(2)))
    broken = ChainVerdict(entries_checked=1, problems=["entry 1: boom"])
    assert "BROKEN" in str(broken)
    assert "entry 1: boom" in str(broken)


def test_verify_rows_accepts_orm_like_objects() -> None:
    class Row:
        def __init__(self, view: LedgerEntryView) -> None:
            self.sequence_number = view.sequence_number
            self.entry_type = view.entry_type
            self.payload_hash = view.payload_hash
            self.entry_hash = view.entry_hash
            self.payload = view.payload
            self.previous_hash = view.previous_hash

    assert verify_rows([Row(view) for view in _chain(3)]).is_intact

"""Standalone verifier for the append-only payroll ledger hash chain.

The chain is written in :mod:`app.core.payroll_engine` at commit time. This
module re-derives it independently, from nothing but the stored rows, and
reports where it diverges.

Keeping it separate from the writer is the entire point. A verifier that shares
the writer's helpers only proves the code is self-consistent; it would happily
confirm a chain built with a mistaken rule. The one thing both sides must agree
on is the hash construction, which is restated here rather than imported:

    payload_hash = sha256(canonical_json(payload))
    entry_hash   = sha256(f"{previous_hash}:{payload_hash}:{sequence}:{entry_type}")

If that construction ever changes, this module has to be changed deliberately —
which is the review moment we want.

Everything here is a pure function over plain dictionaries, so it runs against a
database export, an API response or a test fixture without a session.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any

GENESIS_PREVIOUS_HASH = ""


def canonical_json(payload: dict[str, Any]) -> str:
    """Byte-stable JSON: sorted keys, no incidental whitespace."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def payload_hash(payload: dict[str, Any]) -> str:
    return sha256(canonical_json(payload).encode()).hexdigest()


def entry_hash(
    previous_hash: str | None,
    payload_digest: str,
    sequence_number: int,
    entry_type: str,
) -> str:
    material = (
        f"{previous_hash or GENESIS_PREVIOUS_HASH}:{payload_digest}"
        f":{sequence_number}:{entry_type}"
    )
    return sha256(material.encode()).hexdigest()


@dataclass(frozen=True)
class LedgerEntryView:
    """The subset of a ledger row the chain depends on."""

    sequence_number: int
    entry_type: str
    payload_hash: str
    entry_hash: str
    payload: dict[str, Any]
    previous_hash: str | None = None

    @classmethod
    def from_row(cls, row: Any) -> LedgerEntryView:
        """Build from an ORM row or any object exposing the same attributes."""
        return cls(
            sequence_number=row.sequence_number,
            entry_type=row.entry_type,
            payload_hash=row.payload_hash,
            entry_hash=row.entry_hash,
            payload=row.payload,
            previous_hash=row.previous_hash,
        )


@dataclass
class ChainVerdict:
    """Outcome of verifying one tenant's chain."""

    entries_checked: int = 0
    problems: list[str] = field(default_factory=list)

    @property
    def is_intact(self) -> bool:
        return not self.problems

    def __str__(self) -> str:
        if self.is_intact:
            return f"ledger intact: {self.entries_checked} entries verified"
        lines = [f"ledger BROKEN: {len(self.problems)} problem(s)"]
        lines.extend(f"  - {problem}" for problem in self.problems)
        return "\n".join(lines)


def verify_chain(entries: list[LedgerEntryView]) -> ChainVerdict:
    """Verify sequence, linkage and both hashes for a tenant's whole ledger.

    Entries may arrive in any order; they are sorted by sequence number first.
    Every problem found is reported rather than stopping at the first, because
    the shape of a break is diagnostic — a single bad entry is corruption, a
    break plus every subsequent link failing is a rewrite.
    """
    verdict = ChainVerdict()
    ordered = sorted(entries, key=lambda e: e.sequence_number)
    verdict.entries_checked = len(ordered)

    expected_previous: str | None = None
    expected_sequence = 1

    for entry in ordered:
        label = f"entry {entry.sequence_number}"

        if entry.sequence_number != expected_sequence:
            verdict.problems.append(
                f"{label}: expected sequence {expected_sequence} — "
                f"the chain has a gap or a duplicate"
            )
            expected_sequence = entry.sequence_number

        if entry.previous_hash != expected_previous:
            verdict.problems.append(
                f"{label}: previous_hash does not match the preceding entry_hash"
            )

        recomputed_payload = payload_hash(entry.payload)
        if recomputed_payload != entry.payload_hash:
            verdict.problems.append(
                f"{label}: payload_hash does not match the stored payload — "
                f"the payload was altered after it was written"
            )

        recomputed_entry = entry_hash(
            entry.previous_hash,
            entry.payload_hash,
            entry.sequence_number,
            entry.entry_type,
        )
        if recomputed_entry != entry.entry_hash:
            verdict.problems.append(f"{label}: entry_hash does not match its own fields")

        expected_previous = entry.entry_hash
        expected_sequence += 1

    return verdict


def verify_rows(rows: list[Any]) -> ChainVerdict:
    """Convenience wrapper for ORM rows straight out of a query."""
    return verify_chain([LedgerEntryView.from_row(row) for row in rows])

"""SAFETY_LEDGER — append-only, hash-chained JSONL.

Schema canonicalized in `docs/schemas/ledger-safety.yaml` (status: canonical
as of Phase 4a). Row field semantics live in `docs/04-ARCHITECTURE.md`
§ "Safety Ledger row schema". This module is the single implementation
that writes and verifies the ledger. No other file in `orchestrator/safety/`
touches the file directly.

Properties guaranteed.

  - Append-only: `append(verdict)` opens the file in `"ab"` mode; there is
    no call path in this module that seeks or truncates.
  - Hash-chained: every row's `prev_hash` == previous row's `this_hash`.
    Any in-place edit, delete, or insertion breaks the chain.
  - Canonical bytes: `json.dumps(..., sort_keys=True,
    separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Byte-exact
    across platforms.
  - Candidate-content-free: the candidate text is NEVER written; only its
    sha256 (as `candidate_sha256`) is recorded. This makes the ledger
    publishable without leaking caller content.

Non-properties (honestly stated).

  - Tail truncation is not detected by the chain alone. Truncation defense
    acquires the chain head pinned to Arweave in Phase 4b. Until then,
    `chain_tip(path)` returns the current tip hash so operators can pin it
    out-of-band.
  - Concurrent writers are NOT supported. One `append()` at a time; a
    process-level `threading.Lock` is held around the read+write. Multi-
    process coordination is Phase 5's job (the Relay runs one Arbiter).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from orchestrator.safety.types import Decision, EscalationReason, Verdict

SCHEMA_VERSION = 1
"""Matches `docs/schemas/ledger-safety.yaml` schema_version."""

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger."""

_FILE_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        lock = _FILE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[key] = lock
        return lock


def _canonical_bytes_excluding_this_hash(row: dict[str, Any]) -> bytes:
    """Canonicalization rule. MUST match `docs/schemas/ledger-safety.yaml`
    `hash.canonicalization` exactly."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_hex(text.encode("utf-8"))


def _row_from_verdict(
    verdict: Verdict,
    *,
    seq: int,
    prev_hash: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "timestamp_utc_ns": verdict.timestamp_utc_ns,
        "correlation_id": verdict.correlation_id,
        "candidate_sha256": verdict.candidate_sha256,
        "verdict": verdict.decision.value,
        "summary": verdict.summary,
    }
    if verdict.principle_id is not None:
        row["principle_id"] = verdict.principle_id
    else:
        row["principle_id"] = None
    if verdict.rule_id is not None:
        row["rule_id"] = verdict.rule_id
    else:
        row["rule_id"] = None
    if verdict.rule_version is not None:
        row["rule_version"] = verdict.rule_version
    else:
        row["rule_version"] = None
    if verdict.escalation_reason is not None:
        row["escalation_reason"] = verdict.escalation_reason.value
    else:
        row["escalation_reason"] = None

    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    return row


# -------------------------------------------------------------------- READING


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    """Yield every row in file order. Does not verify the chain."""
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if not line:
                continue
            yield json.loads(line.decode("utf-8"))


def _read_tail(path: Path) -> tuple[int, str]:
    """Return (next_seq, prev_hash) to use for a fresh append.

    For an empty / missing file: (0, ZERO_HASH).
    For an existing file: (last_seq + 1, last_this_hash).
    """
    last_seq = -1
    last_this_hash = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        last_this_hash = str(row["this_hash"])
    return last_seq + 1, last_this_hash


def chain_tip(path: Path) -> tuple[int, str]:
    """Return (seq_count, tip_hash). `seq_count` == number of rows; `tip_hash`
    == last row's `this_hash`, or ZERO_HASH if the file is empty/missing.

    Operators can pin `tip_hash` out-of-band (e.g., a weekly Arweave post
    in Phase 4a) to gain tail-truncation defense manually, ahead of Phase 4b
    automating it.
    """
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


# -------------------------------------------------------------------- WRITING


def append(path: Path, verdict: Verdict) -> dict[str, Any]:
    """Append a verdict to the ledger. Returns the written row.

    Thread-safe within a process (per-path lock). Not multiprocess-safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = _row_from_verdict(verdict, seq=next_seq, prev_hash=prev_hash)
        line = json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        # Open with O_APPEND so even a racing writer from the same process
        # (that bypasses the lock) cannot overwrite an existing row. We
        # still hold the lock for atomicity across the read_tail+write pair.
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return row


# -------------------------------------------------------------------- VERIFY


class ChainBroken(Exception):
    """Raised by `verify_chain` when the ledger fails a structural check.
    The message names the offending `seq` and the specific property that
    failed. Callers: catch and print; do not unwind silently."""


def verify_chain(path: Path) -> tuple[int, str]:
    """Walk the ledger and verify:
      (a) every row is well-formed JSON and includes every required field,
      (b) seq is contiguous starting at 0,
      (c) every this_hash matches recomputed canonical-bytes hash,
      (d) every prev_hash matches the prior row's this_hash.

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None

    for row in iter_rows(path):
        # required-field presence
        for f in (
            "schema_version", "seq", "prev_hash", "this_hash",
            "timestamp_utc_ns", "correlation_id", "candidate_sha256",
            "verdict", "summary",
        ):
            if f not in row:
                raise ChainBroken(f"seq={row.get('seq', '?')}: missing required field {f!r}")

        # schema version
        if int(row["schema_version"]) != SCHEMA_VERSION:
            raise ChainBroken(
                f"seq={row['seq']}: schema_version={row['schema_version']} "
                f"not supported by verifier (knows {SCHEMA_VERSION})"
            )

        # seq contiguity
        if int(row["seq"]) != expected_seq:
            raise ChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )

        # prev_hash linkage
        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(
                f"seq={row['seq']}: prev_hash={row['prev_hash']} "
                f"!= expected {expected_prev}"
            )

        # this_hash recompute
        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(
                f"seq={row['seq']}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        # verdict enum
        if row["verdict"] not in ("ok", "refuse", "escalate"):
            raise ChainBroken(
                f"seq={row['seq']}: invalid verdict {row['verdict']!r}"
            )

        # conditional fields
        if row["verdict"] == "ok":
            if row.get("principle_id") is not None:
                raise ChainBroken(
                    f"seq={row['seq']}: verdict=ok but principle_id is not null"
                )
        else:
            if row.get("principle_id") is None:
                raise ChainBroken(
                    f"seq={row['seq']}: verdict={row['verdict']} requires principle_id"
                )
        if row["verdict"] == "refuse":
            if row.get("rule_id") is None or row.get("rule_version") is None:
                raise ChainBroken(
                    f"seq={row['seq']}: verdict=refuse requires rule_id and rule_version"
                )
        if row["verdict"] == "escalate":
            if row.get("escalation_reason") is None:
                raise ChainBroken(
                    f"seq={row['seq']}: verdict=escalate requires escalation_reason"
                )

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


# ------------------------------------------------------- convenience factory


def build_verdict(
    *,
    correlation_id: str,
    candidate: str,
    timestamp_utc_ns: int,
    decision: Decision,
    summary: str,
    principle_id: str | None = None,
    rule_id: str | None = None,
    rule_version: int | None = None,
    escalation_reason: EscalationReason | None = None,
    rules_run: tuple[str, ...] = (),
) -> Verdict:
    """Build a Verdict with `candidate_sha256` computed from `candidate`.

    The Verdict object is the shape `api.gate()` returns; this helper is
    used by `api.gate()` and by the test suite to avoid re-implementing
    the candidate hash in two places.
    """
    return Verdict(
        decision=decision,
        correlation_id=correlation_id,
        candidate_sha256=_sha256_text(candidate),
        timestamp_utc_ns=timestamp_utc_ns,
        summary=summary,
        principle_id=principle_id,
        rule_id=rule_id,
        rule_version=rule_version,
        escalation_reason=escalation_reason,
        rules_run=rules_run,
    )


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "append",
    "build_verdict",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]

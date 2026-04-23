"""REQUEST_LEDGER — append-only, hash-chained JSONL (Relay-side).

Schema canonicalized in `docs/schemas/ledger-request.yaml` (status:
canonical as of Phase 5a). Row field semantics live in
`docs/04-ARCHITECTURE.md` § "REQUEST_LEDGER row schema (Relay-side, Phase
5a)". This module is the single implementation that writes and verifies
the ledger. No other file in `orchestrator/relay/` touches the file
directly.

REQUEST_LEDGER is the substrate of `xion-verify refund-fidelity`. It
records, per turn, what the Relay was asked to do and what it told the
caller. The cross-ledger join against `SAFETY_LEDGER` (on
`correlation_id`) closes the property "no user-visible response without
a paired Arbiter verdict."

Properties guaranteed.

  - Append-only: `append(...)` opens the file in `O_APPEND`; there is
    no call path in this module that seeks or truncates.
  - Hash-chained: every row's `prev_hash` == previous row's `this_hash`.
    Any in-place edit, delete, or insertion breaks the chain.
  - Canonical bytes: `json.dumps(..., sort_keys=True,
    separators=(",", ":"), ensure_ascii=False).encode("utf-8")`. Byte-
    exact across platforms. Identical rule to SAFETY_LEDGER.
  - Content-free: the candidate text and its hash are NEVER written
    here; SAFETY_LEDGER carries `candidate_sha256` for the joined row.
    Storing it again would tempt readers to trust this ledger as
    ground truth for content (it is not).
  - correlation_id unique: at schema_version 1, every row's
    `correlation_id` is unique within the file. The verifier enforces
    this; v2 (future, when the LLM pipeline lands) relaxes it.

Non-properties (honestly stated).

  - No Arweave anchor loop yet (KW-RELAY-004). Same Layer-2 mechanism
    as SAFETY_LEDGER will eventually apply.
  - Concurrent writers are NOT supported. Per-process `threading.Lock`
    held around read+write. Multi-process Relay is Phase 6's job.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
"""Current REQUEST_LEDGER schema version. Matches
`docs/schemas/ledger-request.yaml`.

History.
  1  Phase 5a (2026-04-21) — Relay-side request record. One row per
                             gate() call; correlation_id unique within
                             this ledger.

Readers MUST accept any schema_version in `_KNOWN_SCHEMA_VERSIONS`.
Writers always write at `SCHEMA_VERSION` (the current version).
"""

_V1_SCHEMA_VERSION = 1
_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset({_V1_SCHEMA_VERSION})

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger."""

_ALLOWED_FINAL_OUTCOMES: frozenset[str] = frozenset({"ok", "refuse", "escalate"})

# Required fields shared by every schema_version (currently only v1 exists).
_V1_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_hash", "this_hash",
    "correlation_id", "state_height",
    "request_arrived_utc_ns", "responded_utc_ns",
    "gate_call_count", "final_outcome",
    "gate_latency_ms_total", "relay_id",
)

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
    """Canonicalization rule. MUST match `docs/schemas/ledger-request.yaml`
    `hash.canonicalization` exactly. Identical rule to SAFETY_LEDGER."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ----------------------------------------------------------- value object


@dataclass(frozen=True)
class RequestRecord:
    """The Relay-side per-turn record. The Relay constructs one of these
    after every handled request and passes it to `append()`.

    Field semantics: see `docs/04-ARCHITECTURE.md` § "REQUEST_LEDGER row
    schema (Relay-side, Phase 5a)".
    """

    correlation_id: str
    state_height: str
    request_arrived_utc_ns: int
    responded_utc_ns: int | None
    gate_call_count: int
    final_outcome: str
    gate_latency_ms_total: int
    relay_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, str) or not self.correlation_id:
            raise ValueError("RequestRecord.correlation_id must be non-empty string")
        if not isinstance(self.state_height, str) or not self.state_height:
            raise ValueError("RequestRecord.state_height must be non-empty string")
        if not isinstance(self.request_arrived_utc_ns, int) or self.request_arrived_utc_ns < 0:
            raise ValueError("RequestRecord.request_arrived_utc_ns must be non-negative int")
        if self.responded_utc_ns is not None and (
            not isinstance(self.responded_utc_ns, int) or self.responded_utc_ns < 0
        ):
            raise ValueError("RequestRecord.responded_utc_ns must be non-negative int or None")
        if not isinstance(self.gate_call_count, int) or self.gate_call_count < 0:
            raise ValueError("RequestRecord.gate_call_count must be non-negative int")
        if self.final_outcome not in _ALLOWED_FINAL_OUTCOMES:
            raise ValueError(
                f"RequestRecord.final_outcome must be one of {sorted(_ALLOWED_FINAL_OUTCOMES)}, "
                f"got {self.final_outcome!r}"
            )
        if not isinstance(self.gate_latency_ms_total, int) or self.gate_latency_ms_total < 0:
            raise ValueError("RequestRecord.gate_latency_ms_total must be non-negative int")
        if not isinstance(self.relay_id, str) or not self.relay_id:
            raise ValueError("RequestRecord.relay_id must be non-empty string")
        # state_height is the prefix of correlation_id (before the colon)
        # at schema_version 1. Enforce here so a malformed pair never
        # reaches disk; the verifier enforces the same property on read.
        if ":" in self.correlation_id:
            prefix = self.correlation_id.split(":", 1)[0]
            if prefix != self.state_height:
                raise ValueError(
                    f"RequestRecord: state_height={self.state_height!r} does not match "
                    f"correlation_id prefix {prefix!r}"
                )


def _row_from_record(
    record: RequestRecord,
    *,
    seq: int,
    prev_hash: str,
) -> dict[str, Any]:
    """Build a new-row dict at `SCHEMA_VERSION`. Writers always produce the
    current version; readers dispatch per-row to handle older versions."""
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "correlation_id": record.correlation_id,
        "state_height": record.state_height,
        "request_arrived_utc_ns": record.request_arrived_utc_ns,
        "responded_utc_ns": record.responded_utc_ns,
        "gate_call_count": record.gate_call_count,
        "final_outcome": record.final_outcome,
        "gate_latency_ms_total": record.gate_latency_ms_total,
        "relay_id": record.relay_id,
    }
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
    """Return (seq_count, tip_hash). `seq_count` == number of rows;
    `tip_hash` == last row's `this_hash`, or ZERO_HASH if the file is
    empty/missing."""
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


# -------------------------------------------------------------------- WRITING


def append(path: Path, record: RequestRecord) -> dict[str, Any]:
    """Append a record to REQUEST_LEDGER. Returns the written row.

    Thread-safe within a process (per-path lock). Not multiprocess-safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = _row_from_record(record, seq=next_seq, prev_hash=prev_hash)
        line = json.dumps(
            row,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8") + b"\n"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line)
        finally:
            os.close(fd)
        return row


# -------------------------------------------------------------------- VERIFY


class ChainBroken(Exception):
    """Raised by `verify_chain` when REQUEST_LEDGER fails a structural
    check. The message names the offending `seq` and the specific
    property that failed."""


def verify_chain(path: Path) -> tuple[int, str]:
    """Walk REQUEST_LEDGER and verify, for every row:
      (a) well-formed JSON with every required field for its schema_version,
      (b) seq contiguous starting at 0,
      (c) this_hash matches recomputed canonical-bytes hash,
      (d) prev_hash matches the prior row's this_hash,
      (e) final_outcome is in the allowed enum,
      (f) state_height equals the prefix of correlation_id (before ':'),
      (g) correlation_id is unique within the file (v1 invariant).

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None
    seen_correlation_ids: set[str] = set()

    for row in iter_rows(path):
        seq = row.get("seq", "?")

        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError, KeyError):
            raise ChainBroken(
                f"seq={seq}: schema_version missing or non-int: {row.get('schema_version')!r}"
            ) from None
        if sv not in _KNOWN_SCHEMA_VERSIONS:
            raise ChainBroken(
                f"seq={seq}: schema_version={sv} not supported by verifier "
                f"(knows {sorted(_KNOWN_SCHEMA_VERSIONS)})"
            )

        for f in _V1_REQUIRED_FIELDS:
            if f not in row:
                raise ChainBroken(f"seq={seq}: missing required field {f!r}")

        if int(row["seq"]) != expected_seq:
            raise ChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )

        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(
                f"seq={seq}: prev_hash={row['prev_hash']} != expected {expected_prev}"
            )

        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(
                f"seq={seq}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        if row["final_outcome"] not in _ALLOWED_FINAL_OUTCOMES:
            raise ChainBroken(
                f"seq={seq}: final_outcome={row['final_outcome']!r} not in "
                f"{sorted(_ALLOWED_FINAL_OUTCOMES)}"
            )

        cid = str(row["correlation_id"])
        sh = str(row["state_height"])
        if ":" in cid:
            prefix = cid.split(":", 1)[0]
            if prefix != sh:
                raise ChainBroken(
                    f"seq={seq}: state_height={sh!r} does not match correlation_id "
                    f"prefix {prefix!r}"
                )

        if cid in seen_correlation_ids:
            raise ChainBroken(
                f"seq={seq}: correlation_id={cid!r} appears more than once "
                f"(unique within REQUEST_LEDGER at schema_version 1)"
            )
        seen_correlation_ids.add(cid)

        # Type spot-checks on the integer fields. A missing or non-int value
        # would already break the hash recomputation, but a typed message is
        # more useful at the failure site.
        for int_field in (
            "request_arrived_utc_ns",
            "gate_call_count",
            "gate_latency_ms_total",
        ):
            v = row[int_field]
            if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                raise ChainBroken(
                    f"seq={seq}: {int_field} must be a non-negative int, got {v!r}"
                )
        rn = row["responded_utc_ns"]
        if rn is not None and (not isinstance(rn, int) or isinstance(rn, bool) or rn < 0):
            raise ChainBroken(
                f"seq={seq}: responded_utc_ns must be a non-negative int or null, got {rn!r}"
            )

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "RequestRecord",
    "append",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]

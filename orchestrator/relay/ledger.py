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
"""REQUEST_LEDGER default writer schema version for ``append()`` (gate-
call rows). Matches `docs/schemas/ledger-request.yaml`. Chat-handler
provider-attempt rows are written at schema_version 2 via
``append_provider_attempt()``; the reader accepts both.

History.
  1  Phase 5a (2026-04-21) — Relay-side gate-call record. One row per
                             gate() call; correlation_id unique within
                             this ledger.
  2  Phase 5g-vii (2026-04-23) — Chat-handler provider-attempt record.
                             One row per provider attempt of a chat
                             turn. Multiple rows may share a
                             ``chat_turn_id``. Carries
                             ``attempt_index``, ``provider_id``,
                             ``outcome``, ``failure_reason_class``.
                             Releases the v1 correlation_id-unique
                             invariant on v2 rows (v1 rows still hold
                             it). Doctrine anchor:
                             `docs/26-INFERENCE-POLICY.md` § "Provider
                             fallback semantics" P3.

Readers MUST accept any schema_version in `_KNOWN_SCHEMA_VERSIONS`.
Writers choose per-call: Relay gate-call writes still emit v1 (via
``append``); chat-handler provider-attempt writes emit v2 (via
``append_provider_attempt``).
"""

_V1_SCHEMA_VERSION = 1
_V2_SCHEMA_VERSION = 2
_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset(
    {_V1_SCHEMA_VERSION, _V2_SCHEMA_VERSION}
)

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger."""

_ALLOWED_FINAL_OUTCOMES: frozenset[str] = frozenset({"ok", "refuse", "escalate"})

_ALLOWED_V2_OUTCOMES: frozenset[str] = frozenset({"success", "failure"})
"""Allowed values for REQUEST_LEDGER v2 ``outcome`` field.

Pinned by `docs/26-INFERENCE-POLICY.md` § "Provider fallback semantics"
P5 (``success`` + six failure classes, with ``outcome=failure`` tagged
by ``failure_reason_class``).
"""

_ALLOWED_V2_FAILURE_REASON_CLASSES: frozenset[str] = frozenset(
    {
        "insufficient_credits",
        "rate_limited_upstream",
        "provider_unreachable",
        "timeout",
        "moderation_refusal",
        "unknown_provider_error",
    }
)
"""Allowed values for REQUEST_LEDGER v2 ``failure_reason_class`` field
when ``outcome == "failure"``. MUST equal the P5 table in
`docs/26-INFERENCE-POLICY.md` and the ``FAILURE_REASON_CLASSES`` tuple
exported by `orchestrator/inference_router/provider.py`. The refund-
fidelity verifier extension (C5) asserts the equality; drift is a
doctrine violation, not an implementation bug."""

_V1_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_hash", "this_hash",
    "correlation_id", "state_height",
    "request_arrived_utc_ns", "responded_utc_ns",
    "gate_call_count", "final_outcome",
    "gate_latency_ms_total", "relay_id",
)

_V2_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_hash", "this_hash",
    "correlation_id", "state_height", "relay_id",
    "request_arrived_utc_ns", "responded_utc_ns",
    "chat_turn_id", "attempt_index",
    "provider_id", "outcome", "failure_reason_class",
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
    """Build a v1 gate-call row dict.

    Relay gate-call writers keep emitting v1 (the gate-call row shape
    pre-dates provider-attempt semantics). Readers dispatch per-row by
    ``schema_version``. See ``_row_from_provider_attempt`` for v2.
    """
    row: dict[str, Any] = {
        "schema_version": _V1_SCHEMA_VERSION,
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


# --------------------------- v2 provider-attempt record (Phase 5g-vii)


@dataclass(frozen=True)
class ProviderAttemptRecord:
    """The chat-handler-side per-provider-attempt record.

    Written by ``orchestrator/api/chat.py`` inside the
    ``select_ordered()`` fallback loop: one record per attempted
    provider, regardless of outcome. Doctrine anchor:
    ``docs/26-INFERENCE-POLICY.md`` § "Provider fallback semantics" P3.

    Shape relative to ``RequestRecord`` (v1):
      - SHARED: ``correlation_id``, ``state_height``, ``relay_id``,
        ``request_arrived_utc_ns``, ``responded_utc_ns``. These let a
        reader align the attempt row with the Relay-side gate-call row
        (via ``correlation_id``) when they want to cross-reference
        ingress moderation against the turn.
      - NEW in v2: ``chat_turn_id`` (opaque 32-hex-char turn id,
        generated by the chat handler to link all attempts of a
        single turn), ``attempt_index`` (0-based contiguous within a
        turn), ``provider_id`` (which provider this attempt ran
        against), ``outcome`` (``success`` | ``failure``),
        ``failure_reason_class`` (one of the P5 values, or ``null`` on
        success).
      - DROPPED from v2: ``gate_call_count``, ``final_outcome``,
        ``gate_latency_ms_total`` (these are gate-call fields; v2 rows
        are provider-attempt rows).

    The correlation_id on a v2 row is the Relay-side ingress
    correlation_id (i.e., the same correlation_id the v1 gate-call row
    for ingress wrote). Multiple v2 rows may share this
    correlation_id — the v1 uniqueness invariant is v1-only.
    """

    correlation_id: str
    state_height: str
    relay_id: str
    request_arrived_utc_ns: int
    responded_utc_ns: int | None
    chat_turn_id: str
    attempt_index: int
    provider_id: str
    outcome: str  # "success" | "failure"
    failure_reason_class: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, str) or not self.correlation_id:
            raise ValueError(
                "ProviderAttemptRecord.correlation_id must be non-empty str"
            )
        if not isinstance(self.state_height, str) or not self.state_height:
            raise ValueError(
                "ProviderAttemptRecord.state_height must be non-empty str"
            )
        if not isinstance(self.relay_id, str) or not self.relay_id:
            raise ValueError(
                "ProviderAttemptRecord.relay_id must be non-empty str"
            )
        if (
            not isinstance(self.request_arrived_utc_ns, int)
            or isinstance(self.request_arrived_utc_ns, bool)
            or self.request_arrived_utc_ns < 0
        ):
            raise ValueError(
                "ProviderAttemptRecord.request_arrived_utc_ns must be "
                "non-negative int"
            )
        if self.responded_utc_ns is not None and (
            not isinstance(self.responded_utc_ns, int)
            or isinstance(self.responded_utc_ns, bool)
            or self.responded_utc_ns < 0
        ):
            raise ValueError(
                "ProviderAttemptRecord.responded_utc_ns must be "
                "non-negative int or None"
            )
        if not isinstance(self.chat_turn_id, str) or not self.chat_turn_id:
            raise ValueError(
                "ProviderAttemptRecord.chat_turn_id must be non-empty str"
            )
        if (
            not isinstance(self.attempt_index, int)
            or isinstance(self.attempt_index, bool)
            or self.attempt_index < 0
        ):
            raise ValueError(
                "ProviderAttemptRecord.attempt_index must be non-negative int"
            )
        if not isinstance(self.provider_id, str) or not self.provider_id:
            raise ValueError(
                "ProviderAttemptRecord.provider_id must be non-empty str"
            )
        if self.outcome not in _ALLOWED_V2_OUTCOMES:
            raise ValueError(
                f"ProviderAttemptRecord.outcome must be one of "
                f"{sorted(_ALLOWED_V2_OUTCOMES)}, got {self.outcome!r}"
            )
        if self.outcome == "success":
            if self.failure_reason_class is not None:
                raise ValueError(
                    "ProviderAttemptRecord.failure_reason_class MUST be "
                    "None when outcome='success'"
                )
        else:
            if self.failure_reason_class not in _ALLOWED_V2_FAILURE_REASON_CLASSES:
                raise ValueError(
                    "ProviderAttemptRecord.failure_reason_class must be one "
                    f"of {sorted(_ALLOWED_V2_FAILURE_REASON_CLASSES)} when "
                    f"outcome='failure', got {self.failure_reason_class!r}"
                )


def _row_from_provider_attempt(
    record: ProviderAttemptRecord,
    *,
    seq: int,
    prev_hash: str,
) -> dict[str, Any]:
    """Build a v2 provider-attempt row dict."""
    row: dict[str, Any] = {
        "schema_version": _V2_SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "correlation_id": record.correlation_id,
        "state_height": record.state_height,
        "relay_id": record.relay_id,
        "request_arrived_utc_ns": record.request_arrived_utc_ns,
        "responded_utc_ns": record.responded_utc_ns,
        "chat_turn_id": record.chat_turn_id,
        "attempt_index": record.attempt_index,
        "provider_id": record.provider_id,
        "outcome": record.outcome,
        "failure_reason_class": record.failure_reason_class,
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
    """Append a v1 gate-call record to REQUEST_LEDGER. Returns the written row.

    Used by the Relay for per-``evaluate()`` gate-call writes. Chat
    handler provider-attempt writes go through
    ``append_provider_attempt`` instead.

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


def append_provider_attempt(
    path: Path, record: ProviderAttemptRecord
) -> dict[str, Any]:
    """Append a v2 provider-attempt record to REQUEST_LEDGER.

    Used by ``orchestrator/api/chat.py``'s fallback loop: exactly one
    record per attempted provider, regardless of outcome. See
    ``ProviderAttemptRecord`` for field semantics and the doctrine
    anchor.

    Thread-safe within a process (per-path lock). Shares the same
    per-path lock as ``append`` so v1 and v2 writes against the same
    file interleave safely.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = _row_from_provider_attempt(
            record, seq=next_seq, prev_hash=prev_hash
        )
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
    """Walk REQUEST_LEDGER and verify structural invariants.

    Per-row version dispatch. For every row:
      (a) well-formed JSON with every required field for its schema_version,
      (b) seq contiguous starting at 0,
      (c) this_hash matches recomputed canonical-bytes hash,
      (d) prev_hash matches the prior row's this_hash,
      (e) state_height equals the prefix of correlation_id (before ':'),

    For v1 rows additionally:
      (f) final_outcome is in the allowed enum,
      (g) correlation_id is unique among v1 rows within the file.

    For v2 rows additionally:
      (h) outcome is "success" or "failure",
      (i) failure_reason_class is one of the pinned six or null,
      (j) (chat_turn_id, attempt_index) is unique within the file, and
          attempt_indexes within a given chat_turn_id are contiguous
          starting at 0.

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None
    seen_v1_correlation_ids: set[str] = set()
    attempts_per_turn: dict[str, list[int]] = {}

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

        required = _V1_REQUIRED_FIELDS if sv == _V1_SCHEMA_VERSION else _V2_REQUIRED_FIELDS
        for f in required:
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

        cid = str(row["correlation_id"])
        sh = str(row["state_height"])
        if ":" in cid:
            prefix = cid.split(":", 1)[0]
            if prefix != sh:
                raise ChainBroken(
                    f"seq={seq}: state_height={sh!r} does not match correlation_id "
                    f"prefix {prefix!r}"
                )

        rn = row["responded_utc_ns"]
        if rn is not None and (not isinstance(rn, int) or isinstance(rn, bool) or rn < 0):
            raise ChainBroken(
                f"seq={seq}: responded_utc_ns must be a non-negative int or null, got {rn!r}"
            )
        r_arr = row["request_arrived_utc_ns"]
        if not isinstance(r_arr, int) or isinstance(r_arr, bool) or r_arr < 0:
            raise ChainBroken(
                f"seq={seq}: request_arrived_utc_ns must be a non-negative int, got {r_arr!r}"
            )

        if sv == _V1_SCHEMA_VERSION:
            if row["final_outcome"] not in _ALLOWED_FINAL_OUTCOMES:
                raise ChainBroken(
                    f"seq={seq}: final_outcome={row['final_outcome']!r} not in "
                    f"{sorted(_ALLOWED_FINAL_OUTCOMES)}"
                )
            for int_field in ("gate_call_count", "gate_latency_ms_total"):
                v = row[int_field]
                if not isinstance(v, int) or isinstance(v, bool) or v < 0:
                    raise ChainBroken(
                        f"seq={seq}: {int_field} must be a non-negative int, got {v!r}"
                    )
            if cid in seen_v1_correlation_ids:
                raise ChainBroken(
                    f"seq={seq}: correlation_id={cid!r} appears more than once "
                    f"(unique within REQUEST_LEDGER v1 rows)"
                )
            seen_v1_correlation_ids.add(cid)
        else:  # v2 provider-attempt row
            outcome = row["outcome"]
            if outcome not in _ALLOWED_V2_OUTCOMES:
                raise ChainBroken(
                    f"seq={seq}: v2 outcome={outcome!r} not in "
                    f"{sorted(_ALLOWED_V2_OUTCOMES)}"
                )
            frc = row["failure_reason_class"]
            if outcome == "success":
                if frc is not None:
                    raise ChainBroken(
                        f"seq={seq}: v2 outcome='success' requires "
                        f"failure_reason_class=null, got {frc!r}"
                    )
            else:
                if frc not in _ALLOWED_V2_FAILURE_REASON_CLASSES:
                    raise ChainBroken(
                        f"seq={seq}: v2 outcome='failure' requires "
                        f"failure_reason_class in "
                        f"{sorted(_ALLOWED_V2_FAILURE_REASON_CLASSES)}, "
                        f"got {frc!r}"
                    )
            ai = row["attempt_index"]
            if not isinstance(ai, int) or isinstance(ai, bool) or ai < 0:
                raise ChainBroken(
                    f"seq={seq}: v2 attempt_index must be non-negative int, got {ai!r}"
                )
            tid = str(row["chat_turn_id"])
            attempts_per_turn.setdefault(tid, []).append(ai)

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    # Post-pass v2 invariant: within each chat_turn_id, the attempt_index
    # sequence must be {0, 1, ..., N-1} in any row order (the chain rows
    # themselves are strictly sequenced by `seq`, but multiple turns may
    # interleave). A gap, duplicate, or missing 0 is a doctrine violation.
    for tid, indexes in attempts_per_turn.items():
        expected_set = set(range(len(indexes)))
        if sorted(indexes) != sorted(expected_set):
            raise ChainBroken(
                f"chat_turn_id={tid!r}: v2 attempt_index sequence "
                f"{sorted(indexes)} is not {{0,1,...,{len(indexes) - 1}}} "
                "(gap, duplicate, or missing 0)"
            )

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "ProviderAttemptRecord",
    "RequestRecord",
    "append",
    "append_provider_attempt",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]

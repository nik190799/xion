"""SENSORIUM_LEDGER — append-only, hash-chained JSONL.

Schema canonicalized in `docs/schemas/ledger-sensorium.yaml` (status:
canonical as of Phase 5c). Row field semantics live in
`docs/04-ARCHITECTURE.md` § "SENSORIUM_LEDGER row schema (Phase 5c)".
This module is the single implementation that writes and verifies the
ledger. No other file in `orchestrator/sensorium/` touches the file
directly.

Properties guaranteed.
  - Append-only: writes go through ``os.O_APPEND``; no call path in
    this module seeks or truncates.
  - Hash-chained: every row's ``prev_hash`` == previous row's
    ``this_hash``. Any in-place edit, delete, or insertion breaks the
    chain.
  - Canonical bytes: same rule as SAFETY_LEDGER / REQUEST_LEDGER —
    ``json.dumps(..., sort_keys=True, separators=(",", ":"),
    ensure_ascii=False).encode("utf-8")``.
  - Content-free: no candidate text, no user identifier, no full
    Sensorium state bytes are written. Only a ``snapshot_hash`` on
    tick_commit rows and a saturated ``distress_score`` on distress
    rows.

Non-properties (honestly stated).
  - Tail truncation is not detected by the chain alone. Anchor loop
    (Arweave) is deferred (sibling of KW-RELAY-004); Phase 5c ships
    the local chain only.
  - Concurrent writers are NOT supported; a per-path
    ``threading.Lock`` is held around the read-tail + write pair.
  - Cross-ledger join to SAFETY_LEDGER on ``correlation_id`` is
    structurally possible today AND is walked by ``xion-verify
    crisis-fidelity`` as of Phase 5d. Distress rows with
    ``correlation_id=null`` remain legal (tick-time or test-harness
    observations) and are tallied separately by the verifier without
    FAIL; distress rows with a non-null ``correlation_id`` MUST have a
    paired SAFETY row with ``decision=escalate``, ``principle_id="10"``,
    ``escalation_reason=model_review_required``.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from orchestrator.sensorium.sensorium import SensoriumState

SCHEMA_VERSION = 1
_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})

ZERO_HASH = "0" * 64
"""prev_hash sentinel for seq=0 of a fresh ledger."""

_ALLOWED_EVENT_TYPES: frozenset[str] = frozenset({"distress", "tick_commit"})
_ALLOWED_CHANNELS: frozenset[str] = frozenset({"textual", "paralinguistic"})

_COMMON_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "seq",
    "prev_hash",
    "this_hash",
    "as_of_utc_ns",
    "event_type",
    "channel",
    "relay_id",
)
# The two conditional fields' required-presence is per-event-type;
# correlation_id is conditional on "distress && joined to gate()".
_CONDITIONAL_PER_EVENT_TYPE: dict[str, tuple[str, ...]] = {
    "distress": ("distress_score",),
    "tick_commit": ("snapshot_hash",),
}

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
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_state_hash(state: SensoriumState) -> str:
    """Compute the canonical hash of a `SensoriumState`. Used by
    `append_tick_commit` and by verifiers that want to re-pin a
    snapshot out-of-band.
    """
    payload = state.to_dict()
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return _sha256_hex(canonical)


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
    last_seq = -1
    last_this_hash = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        last_this_hash = str(row["this_hash"])
    return last_seq + 1, last_this_hash


def chain_tip(path: Path) -> tuple[int, str]:
    """Return (row_count, tip_hash). `tip_hash` == ZERO_HASH for an
    empty / missing file."""
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


# -------------------------------------------------------------------- WRITING


def _append_row(path: Path, row_body: dict[str, Any]) -> dict[str, Any]:
    """Write a row with ``seq`` + ``prev_hash`` + ``this_hash`` filled
    in from the current tail. Thread-safe within a process (per-path
    lock). Not multiprocess-safe.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        next_seq, prev_hash = _read_tail(path)
        row = dict(row_body)
        row["schema_version"] = SCHEMA_VERSION
        row["seq"] = next_seq
        row["prev_hash"] = prev_hash
        row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
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


def append_distress(
    path: Path,
    *,
    distress_score: float,
    channel: str,
    as_of_utc_ns: int,
    relay_id: str,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Append a ``distress`` event row. ``distress_score`` is
    saturated to [0.0, 1.0]; ``channel`` must be one of
    ``{"textual", "paralinguistic"}``. ``correlation_id`` is present
    iff the distress was joined to a ``gate()`` call.
    """
    if channel not in _ALLOWED_CHANNELS:
        raise ValueError(f"channel must be one of {sorted(_ALLOWED_CHANNELS)}, got {channel!r}")
    clamped = max(0.0, min(1.0, float(distress_score)))
    body: dict[str, Any] = {
        "as_of_utc_ns": int(as_of_utc_ns),
        "event_type": "distress",
        "channel": channel,
        "distress_score": clamped,
        "snapshot_hash": None,
        "correlation_id": correlation_id,
        "relay_id": str(relay_id),
    }
    return _append_row(path, body)


def append_distress_from_state(
    path: Path,
    *,
    state: SensoriumState,
    correlation_id: str | None,
    relay_id: str,
) -> dict[str, Any]:
    """Append a ``distress`` row using the fields of ``state.distress``.

    Convenience wrapper around ``append_distress`` for callers that have a
    ``SensoriumState`` in hand and want to record its current DistressSignal
    against a specific ``correlation_id``. The caller is responsible for
    deciding when to write — this helper does NOT check the score against
    ``DISTRESS_THRESHOLD`` (a caller may legitimately want to record a
    sub-threshold distress observation for forensic continuity, though no
    Phase 5d code path does so).

    Phase 5d is the first production caller: ``orchestrator.safety.api.gate``
    (append_to_ledger=True path) and ``orchestrator.relay.relay.Relay``
    (append_to_ledger=False path) both call this helper when a
    Sensorium-triggered Principle-10 escalation has been rendered, so the
    SENSORIUM distress row is written by exactly one layer per gate() call
    and ``xion-verify crisis-fidelity``'s cross-ledger join holds.

    Raises ``ValueError`` if ``state.distress`` is None (the caller has no
    DistressSignal to record — a programmer error worth failing loudly).
    """
    if state.distress is None:
        raise ValueError("append_distress_from_state(): state has no distress signal")
    return append_distress(
        path,
        distress_score=state.distress.text_distress_score,
        channel=state.distress.source,
        as_of_utc_ns=state.distress.as_of_utc_ns,
        relay_id=relay_id,
        correlation_id=correlation_id,
    )


def append_tick_commit(
    path: Path,
    *,
    state: SensoriumState,
    relay_id: str,
    signals: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Append a ``tick_commit`` row pinning the canonical hash of
    ``state``. Useful for forensic continuity of the Sensorium's
    observed readings without publishing the state bytes themselves.

    Phase 6.4.b: optional ``signals`` carries JSON-serialised ``Signal`` dicts
    for the Nervous System v2 bus (dual-write with legacy ``snapshot_hash``).
    """
    body: dict[str, Any] = {
        "as_of_utc_ns": int(state.as_of_utc_ns),
        "event_type": "tick_commit",
        "channel": "textual",  # neutral default; tick_commit rows carry no real channel
        "distress_score": None,
        "snapshot_hash": canonical_state_hash(state),
        "correlation_id": None,
        "relay_id": str(relay_id),
    }
    if signals is not None and len(signals) > 0:
        body["signals"] = signals
    return _append_row(path, body)


# -------------------------------------------------------------------- VERIFY


class ChainBroken(Exception):
    """Raised by `verify_chain` when the ledger fails a structural
    check. The message names the offending `seq` and the specific
    property that failed.
    """


def verify_chain(path: Path) -> tuple[int, str]:
    """Walk the ledger and verify, for every row:
      (a) well-formed JSON with every required field for its
          schema_version,
      (b) seq contiguous starting at 0,
      (c) this_hash matches recomputed canonical-bytes hash,
      (d) prev_hash matches the prior row's this_hash,
      (e) distress rows carry distress_score and snapshot_hash==null;
          tick_commit rows carry snapshot_hash and distress_score==null;
          neither carries the other,
      (f) event_type and channel are members of their respective enums.

    Returns (row_count, tip_hash). Raises ChainBroken on any failure.
    """
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None

    for row in iter_rows(path):
        seq = row.get("seq", "?")

        for f in _COMMON_REQUIRED_FIELDS:
            if f not in row:
                raise ChainBroken(f"seq={seq}: missing required field {f!r}")

        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError):
            raise ChainBroken(
                f"seq={seq}: schema_version must be an int, got {row['schema_version']!r}"
            ) from None
        if sv not in _KNOWN_SCHEMA_VERSIONS:
            raise ChainBroken(
                f"seq={seq}: schema_version={sv} not supported by verifier "
                f"(knows {sorted(_KNOWN_SCHEMA_VERSIONS)})"
            )

        if int(row["seq"]) != expected_seq:
            raise ChainBroken(
                f"seq non-contiguous: expected {expected_seq}, got {row['seq']}"
            )

        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(
                f"seq={seq}: prev_hash={row['prev_hash']} != expected {expected_prev}"
            )

        event_type = row["event_type"]
        if event_type not in _ALLOWED_EVENT_TYPES:
            raise ChainBroken(
                f"seq={seq}: event_type must be one of {sorted(_ALLOWED_EVENT_TYPES)}, "
                f"got {event_type!r}"
            )
        channel = row["channel"]
        if channel not in _ALLOWED_CHANNELS:
            raise ChainBroken(
                f"seq={seq}: channel must be one of {sorted(_ALLOWED_CHANNELS)}, "
                f"got {channel!r}"
            )

        # Conditional field presence per event_type.
        distress_score = row.get("distress_score")
        snapshot_hash = row.get("snapshot_hash")
        if event_type == "distress":
            if distress_score is None:
                raise ChainBroken(
                    f"seq={seq}: event_type=distress requires distress_score"
                )
            if not isinstance(distress_score, (int, float)) or not (
                0.0 <= float(distress_score) <= 1.0
            ):
                raise ChainBroken(
                    f"seq={seq}: distress_score must be a float in [0.0, 1.0], "
                    f"got {distress_score!r}"
                )
            if snapshot_hash is not None:
                raise ChainBroken(
                    f"seq={seq}: event_type=distress requires snapshot_hash=null"
                )
        elif event_type == "tick_commit":
            if not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
                raise ChainBroken(
                    f"seq={seq}: event_type=tick_commit requires snapshot_hash "
                    f"(64-char hex), got {snapshot_hash!r}"
                )
            if distress_score is not None:
                raise ChainBroken(
                    f"seq={seq}: event_type=tick_commit requires distress_score=null"
                )
            sigs = row.get("signals", None)
            if sigs is not None:
                if not isinstance(sigs, list):
                    raise ChainBroken(
                        f"seq={seq}: tick_commit `signals` must be a list, got {type(sigs).__name__}"
                    )
                for j, s in enumerate(sigs):
                    if not isinstance(s, dict):
                        raise ChainBroken(
                            f"seq={seq}: signals[{j}] must be object, got {type(s).__name__}"
                        )
                    for k in (
                        "kind",
                        "source",
                        "value",
                        "timestamp_utc_ns",
                        "methodology_hash",
                        "confidence",
                        "schema_version",
                    ):
                        if k not in s:
                            raise ChainBroken(
                                f"seq={seq}: signals[{j}] missing {k!r}"
                            )

        # correlation_id is a presence-optional field; type-check if present.
        corr = row.get("correlation_id")
        if corr is not None and not isinstance(corr, str):
            raise ChainBroken(
                f"seq={seq}: correlation_id must be a string or null, got {type(corr).__name__}"
            )

        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(
                f"seq={seq}: this_hash recomputation mismatch "
                f"(stored={row['this_hash']} recomputed={recomputed})"
            )

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip


def tally_by_event_type(path: Path) -> dict[str, dict[str, int]]:
    """Return a ``{event_type: {channel: count}}`` tally. Used by
    ``xion-verify sensorium-ledger`` to surface at-a-glance whether
    distress is being observed and whether the paralinguistic channel
    has started emitting (Phase 6+).
    """
    tally: dict[str, dict[str, int]] = {}
    for row in iter_rows(path):
        et = str(row.get("event_type", "?"))
        ch = str(row.get("channel", "?"))
        tally.setdefault(et, {}).setdefault(ch, 0)
        tally[et][ch] += 1
    return tally


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "append_distress",
    "append_tick_commit",
    "canonical_state_hash",
    "chain_tip",
    "iter_rows",
    "tally_by_event_type",
    "verify_chain",
]

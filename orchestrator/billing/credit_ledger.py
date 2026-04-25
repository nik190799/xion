"""BILLING_LEDGER for inference-credit telemetry (Phase 6.9).

This ledger is intentionally smaller than PAYMENT_LEDGER: it records
provider-side credit state and top-up events, not user payments. The
hash-chain/canonicalization rule mirrors the existing ledgers so
``xion-verify billing-credits-floor`` can detect edits.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1
ZERO_HASH = "0" * 64

_EVENTS = frozenset({"balance_poll", "topup"})
_REQUIRED_FIELDS = (
    "schema_version",
    "seq",
    "prev_hash",
    "this_hash",
    "timestamp_utc_ns",
    "provider_id",
    "event",
    "balance_usd",
    "balance_tao",
    "payment_address",
    "runway_inference_credits_days",
    "tx_hash",
    "spend_authority_reference",
)
_FILE_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


class ChainBroken(Exception):
    pass


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


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if line:
                yield json.loads(line.decode("utf-8"))


def _read_tail(path: Path) -> tuple[int, str]:
    last_seq = -1
    last_hash = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        last_hash = str(row["this_hash"])
    return last_seq + 1, last_hash


def append_billing_row(
    path: Path,
    *,
    provider_id: str,
    event: Literal["balance_poll", "topup"],
    balance_usd: float | None,
    balance_tao: float | None,
    payment_address: str | None,
    runway_inference_credits_days: float | None,
    tx_hash: str | None = None,
    spend_authority_reference: str | None = None,
    timestamp_utc_ns: int | None = None,
) -> dict[str, Any]:
    if event not in _EVENTS:
        raise ValueError(f"event must be one of {sorted(_EVENTS)}, got {event!r}")
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        seq, prev_hash = _read_tail(path)
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "seq": seq,
            "prev_hash": prev_hash,
            "timestamp_utc_ns": timestamp_utc_ns if timestamp_utc_ns is not None else time.time_ns(),
            "provider_id": provider_id,
            "event": event,
            "balance_usd": balance_usd,
            "balance_tao": balance_tao,
            "payment_address": payment_address,
            "runway_inference_credits_days": runway_inference_credits_days,
            "tx_hash": tx_hash,
            "spend_authority_reference": spend_authority_reference,
        }
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


def verify_chain(path: Path) -> tuple[int, str]:
    if not path.is_file():
        return 0, ZERO_HASH
    expected_seq = 0
    expected_prev = ZERO_HASH
    last_hash = ZERO_HASH
    for row in iter_rows(path):
        seq = row.get("seq", "?")
        for field in _REQUIRED_FIELDS:
            if field not in row:
                raise ChainBroken(f"seq={seq}: missing required field {field!r}")
        if int(row["schema_version"]) != SCHEMA_VERSION:
            raise ChainBroken(f"seq={seq}: unknown schema_version={row['schema_version']!r}")
        if int(row["seq"]) != expected_seq:
            raise ChainBroken(f"seq non-contiguous: expected {expected_seq}, got {row['seq']}")
        if str(row["prev_hash"]) != expected_prev:
            raise ChainBroken(f"seq={seq}: prev_hash mismatch")
        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(f"seq={seq}: this_hash recomputation mismatch")
        if row["event"] not in _EVENTS:
            raise ChainBroken(f"seq={seq}: invalid event {row['event']!r}")
        if row["event"] == "topup" and not row["tx_hash"]:
            raise ChainBroken(f"seq={seq}: topup rows require tx_hash")
        last_hash = str(row["this_hash"])
        expected_prev = last_hash
        expected_seq += 1
    return expected_seq, last_hash


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "append_billing_row",
    "iter_rows",
    "verify_chain",
]

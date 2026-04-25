"""ANCHOR_LEDGER — append-only, hash-chained JSONL.

Schema canonicalized in `docs/schemas/ledger-anchor.yaml` (status: canonical).
This module is the single implementation that writes and verifies the ledger.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
LEDGER_NAME = "ANCHOR_LEDGER"
ZERO_HASH = "0" * 64

_KNOWN_SCHEMA_VERSIONS: frozenset[int] = frozenset({1})
_KNOWN_LEDGER_KINDS: frozenset[str] = frozenset({"request", "payment", "safety"})

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
    """Canonicalization. MUST match the schema's `hash.canonicalization` block."""
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ChainBrokenError(Exception):
    """Raised by verify_chain when integrity fails."""
    pass


@dataclass(frozen=True)
class AnchorRecord:
    """An interaction anchor record."""
    schema_version: int
    seq: int
    prev_hash: str
    this_hash: str
    period_start_unix: int
    period_end_unix: int
    ledger_kind: str
    batch_root_sha256: str
    batch_size: int
    leaf_correlation_ids: list[str]
    ao_message_id: str | None = None
    degraded_to_local: bool | None = None

    def __post_init__(self):
        if self.schema_version not in _KNOWN_SCHEMA_VERSIONS:
            raise ValueError(f"Unknown schema_version: {self.schema_version}")
        if self.seq < 0:
            raise ValueError(f"Invalid seq: {self.seq}")
        if not isinstance(self.prev_hash, str) or len(self.prev_hash) != 64:
            raise ValueError(f"Invalid prev_hash: {self.prev_hash}")
        if not isinstance(self.this_hash, str) or len(self.this_hash) != 64:
            raise ValueError(f"Invalid this_hash: {self.this_hash}")
        if self.period_start_unix < 0:
            raise ValueError("period_start_unix must be non-negative")
        if self.period_end_unix <= self.period_start_unix:
            raise ValueError("period_end_unix must be > period_start_unix")
        if self.ledger_kind not in _KNOWN_LEDGER_KINDS:
            raise ValueError(f"Unknown ledger_kind: {self.ledger_kind}")
        if not isinstance(self.batch_root_sha256, str) or len(self.batch_root_sha256) != 64:
            raise ValueError(f"Invalid batch_root_sha256: {self.batch_root_sha256}")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if len(self.leaf_correlation_ids) != self.batch_size:
            raise ValueError("leaf_correlation_ids length must match batch_size")
        
        # Enforce sorted order
        if self.leaf_correlation_ids != sorted(self.leaf_correlation_ids):
            raise ValueError("leaf_correlation_ids must be strictly sorted")

    def to_dict(self) -> dict[str, Any]:
        d = {
            "schema_version": self.schema_version,
            "seq": self.seq,
            "prev_hash": self.prev_hash,
            "this_hash": self.this_hash,
            "period_start_unix": self.period_start_unix,
            "period_end_unix": self.period_end_unix,
            "ledger_kind": self.ledger_kind,
            "batch_root_sha256": self.batch_root_sha256,
            "batch_size": self.batch_size,
            "leaf_correlation_ids": self.leaf_correlation_ids,
        }
        if self.ao_message_id is not None:
            d["ao_message_id"] = self.ao_message_id
        if self.degraded_to_local is not None:
            d["degraded_to_local"] = self.degraded_to_local
        return d


def read_chain(path: str | Path) -> Iterator[AnchorRecord]:
    """Reads records without verifying chain integrity."""
    p = Path(path)
    if not p.exists():
        return
        
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            try:
                yield AnchorRecord(**d)
            except ValueError as e:
                raise ChainBrokenError(f"Invalid record: {e}")


def verify_chain(path: str | Path) -> list[AnchorRecord]:
    """Reads and asserts integrity of the entire chain.

    Returns the list of valid records if unbroken.
    Raises ChainBrokenError on any mismatch.
    """
    records = []
    expected_seq = 0
    expected_prev = ZERO_HASH

    for rec in read_chain(path):
        if rec.seq != expected_seq:
            raise ChainBrokenError(f"seq gap/overlap: expected {expected_seq}, got {rec.seq}")
        if rec.prev_hash != expected_prev:
            raise ChainBrokenError(f"prev_hash mismatch at seq {rec.seq}")

        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(rec.to_dict()))
        if rec.this_hash != recomputed:
            raise ChainBrokenError(f"this_hash mismatch at seq {rec.seq}")

        records.append(rec)
        expected_seq += 1
        expected_prev = rec.this_hash

    return records


def chain_tip(path: str | Path) -> tuple[int, str]:
    """Returns (next_seq, last_hash). Returns (0, ZERO_HASH) if empty."""
    try:
        recs = verify_chain(path)
        if not recs:
            return 0, ZERO_HASH
        last = recs[-1]
        return last.seq + 1, last.this_hash
    except FileNotFoundError:
        return 0, ZERO_HASH


def append(
    path: str | Path,
    period_start_unix: int,
    period_end_unix: int,
    ledger_kind: str,
    batch_root_sha256: str,
    batch_size: int,
    leaf_correlation_ids: list[str],
    ao_message_id: str | None = None,
    degraded_to_local: bool | None = None,
) -> AnchorRecord:
    """Appends a new record to the chain. Verifies chain on write."""
    p = Path(path)
    lock = _lock_for(p)
    
    with lock:
        next_seq, prev_hash = chain_tip(p)

        # Pre-construct to leverage __post_init__ validation without `this_hash`
        proto = {
            "schema_version": SCHEMA_VERSION,
            "seq": next_seq,
            "prev_hash": prev_hash,
            "period_start_unix": period_start_unix,
            "period_end_unix": period_end_unix,
            "ledger_kind": ledger_kind,
            "batch_root_sha256": batch_root_sha256,
            "batch_size": batch_size,
            "leaf_correlation_ids": leaf_correlation_ids,
        }
        if ao_message_id is not None:
            proto["ao_message_id"] = ao_message_id
        if degraded_to_local is not None:
            proto["degraded_to_local"] = degraded_to_local

        this_hash = _sha256_hex(_canonical_bytes_excluding_this_hash(proto))
        proto["this_hash"] = this_hash

        rec = AnchorRecord(**proto)
        encoded = json.dumps(
            rec.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        mode = "ab" if p.exists() else "wb"
        with p.open(mode) as f:
            f.write((encoded + "\n").encode("utf-8"))

        return rec

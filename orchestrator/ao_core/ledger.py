"""STATE_CHAIN_LEDGER — append-only, hash-chained JSONL (Off-chain mirror).

Schema canonicalized in `docs/schemas/ledger-state-chain.yaml` (status:
canonical as of Phase 6.1).

Properties guaranteed:
  - Append-only: `append(...)` opens the file in `O_APPEND`.
  - Hash-chained: every row's `prev_row_sha256` == previous row's `this_hash`.
  - Canonical bytes: `json.dumps(..., sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.
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

ZERO_HASH = "0" * 64

_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version", "seq", "prev_row_sha256", "this_hash",
    "correlation_id", "height", "state_root_sha256", "prev_state_root_sha256",
    "ao_process_id", "ao_message_id", "committed_by", "committed_at_unix",
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
    body = {k: v for k, v in row.items() if k != "this_hash"}
    return json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@dataclass(frozen=True)
class StateChainRecord:
    correlation_id: str
    height: int
    state_root_sha256: str
    prev_state_root_sha256: str
    ao_process_id: str
    ao_message_id: str
    committed_by: str
    committed_at_unix: int

    def __post_init__(self) -> None:
        if not isinstance(self.correlation_id, str) or not self.correlation_id:
            raise ValueError("StateChainRecord.correlation_id must be non-empty string")
        if not isinstance(self.height, int) or self.height < 0:
            raise ValueError("StateChainRecord.height must be non-negative int")
        if not isinstance(self.state_root_sha256, str) or len(self.state_root_sha256) != 64:
            raise ValueError("StateChainRecord.state_root_sha256 must be 64-char hex string")
        if not isinstance(self.prev_state_root_sha256, str) or len(self.prev_state_root_sha256) != 64:
            raise ValueError("StateChainRecord.prev_state_root_sha256 must be 64-char hex string")
        if not isinstance(self.ao_process_id, str) or not self.ao_process_id:
            raise ValueError("StateChainRecord.ao_process_id must be non-empty string")
        if not isinstance(self.ao_message_id, str) or not self.ao_message_id:
            raise ValueError("StateChainRecord.ao_message_id must be non-empty string")
        if not isinstance(self.committed_by, str) or not self.committed_by:
            raise ValueError("StateChainRecord.committed_by must be non-empty string")
        if not isinstance(self.committed_at_unix, int) or self.committed_at_unix < 0:
            raise ValueError("StateChainRecord.committed_at_unix must be non-negative int")


def _row_from_record(
    record: StateChainRecord,
    *,
    seq: int,
    prev_hash: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_row_sha256": prev_hash,
        "correlation_id": record.correlation_id,
        "height": record.height,
        "state_root_sha256": record.state_root_sha256,
        "prev_state_root_sha256": record.prev_state_root_sha256,
        "ao_process_id": record.ao_process_id,
        "ao_message_id": record.ao_message_id,
        "committed_by": record.committed_by,
        "committed_at_unix": record.committed_at_unix,
    }
    row["this_hash"] = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
    return row


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
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
    count = 0
    tip = ZERO_HASH
    for row in iter_rows(path):
        count += 1
        tip = str(row["this_hash"])
    return count, tip


def append(path: Path, record: StateChainRecord) -> dict[str, Any]:
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


class ChainBroken(Exception):
    pass


def verify_chain(path: Path) -> tuple[int, str]:
    if not path.is_file():
        return 0, ZERO_HASH

    expected_seq = 0
    expected_prev = ZERO_HASH
    last_this: str | None = None

    for row in iter_rows(path):
        seq = row.get("seq", "?")

        try:
            sv = int(row["schema_version"])
        except (TypeError, ValueError, KeyError):
            raise ChainBroken(f"seq={seq}: schema_version missing or non-int") from None
        
        if sv != SCHEMA_VERSION:
            raise ChainBroken(f"seq={seq}: schema_version={sv} not supported")

        for f in _REQUIRED_FIELDS:
            if f not in row:
                raise ChainBroken(f"seq={seq}: missing required field {f!r}")

        if int(row["seq"]) != expected_seq:
            raise ChainBroken(f"seq non-contiguous: expected {expected_seq}, got {row['seq']}")

        if str(row["prev_row_sha256"]) != expected_prev:
            raise ChainBroken(f"seq={seq}: prev_row_sha256={row['prev_row_sha256']} != expected {expected_prev}")

        recomputed = _sha256_hex(_canonical_bytes_excluding_this_hash(row))
        if recomputed != str(row["this_hash"]):
            raise ChainBroken(f"seq={seq}: this_hash recomputation mismatch")

        last_this = str(row["this_hash"])
        expected_prev = last_this
        expected_seq += 1

    tip = last_this if last_this is not None else ZERO_HASH
    return expected_seq, tip

__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ChainBroken",
    "StateChainRecord",
    "append",
    "chain_tip",
    "iter_rows",
    "verify_chain",
]

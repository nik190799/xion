"""Shadow inference ledger (Phase 6.9)."""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64
SCHEMA_VERSION = 1
_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def _canonical(row: dict[str, Any]) -> bytes:
    return json.dumps(
        {k: v for k, v in row.items() if k != "this_hash"},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw in fh:
            line = raw.rstrip(b"\n").rstrip(b"\r")
            if line:
                yield json.loads(line.decode("utf-8"))


def _tail(path: Path) -> tuple[int, str]:
    seq = -1
    tip = ZERO_HASH
    for row in iter_rows(path):
        seq = int(row["seq"])
        tip = str(row["this_hash"])
    return seq + 1, tip


def append_shadow_row(
    path: Path,
    *,
    correlation_id: str,
    primary_provider_id: str,
    shadow_provider_id: str,
    primary_model_id: str | None,
    shadow_model_id: str | None,
    primary_sha256: str,
    shadow_sha256: str,
    divergence_score: float,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(path):
        seq, prev_hash = _tail(path)
        row: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "seq": seq,
            "prev_hash": prev_hash,
            "timestamp_utc_ns": time.time_ns(),
            "correlation_id": correlation_id,
            "primary_provider_id": primary_provider_id,
            "shadow_provider_id": shadow_provider_id,
            "primary_model_id": primary_model_id,
            "shadow_model_id": shadow_model_id,
            "primary_sha256": primary_sha256,
            "shadow_sha256": shadow_sha256,
            "divergence_score": divergence_score,
        }
        row["this_hash"] = _sha(_canonical(row))
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, json.dumps(row, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n")
        finally:
            os.close(fd)
        return row


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def divergence(primary: str, shadow: str) -> float:
    if primary == shadow:
        return 0.0
    p = set(primary.lower().split())
    s = set(shadow.lower().split())
    if not p and not s:
        return 0.0
    union = p | s
    return 1.0 - (len(p & s) / len(union))


__all__ = ["append_shadow_row", "divergence", "iter_rows", "text_sha256"]

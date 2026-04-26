"""Anonymized cutoff-event ledger helpers."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

ZERO_HASH = "0" * 64


def _hash(row: dict[str, Any]) -> str:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def append_cutoff_event(path: Path, *, reason_class: str, session_hash: str) -> dict[str, Any]:
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if path.is_file() and line.strip()
    ] if path.is_file() else []
    row = {
        "schema_version": 1,
        "seq": len(rows),
        "prev_hash": rows[-1]["this_hash"] if rows else ZERO_HASH,
        "this_hash": "",
        "as_of_utc_ns": time.time_ns(),
        "reason_class": reason_class,
        "session_hash": session_hash,
    }
    row["this_hash"] = _hash(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
    return row


def verify_cutoff_chain(path: Path) -> tuple[int, str]:
    if not path.is_file():
        return 0, ZERO_HASH
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    prev = ZERO_HASH
    for expected_seq, row in enumerate(rows):
        if row.get("seq") != expected_seq or row.get("prev_hash") != prev:
            raise ValueError(f"row {expected_seq}: chain linkage mismatch")
        if row.get("this_hash") != _hash(row):
            raise ValueError(f"row {expected_seq}: hash mismatch")
        prev = row["this_hash"]
    return len(rows), prev


__all__ = ["append_cutoff_event", "verify_cutoff_chain"]

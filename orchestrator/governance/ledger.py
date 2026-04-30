"""GOVERNANCE_LEDGER writer for state-actor interactions."""

from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

SCHEMA_VERSION = 1
ZERO_HASH = "0" * 64

StateActorClass = Literal["A", "B", "C", "D"]
ResponseCategory = Literal["comply", "refuse", "escalate-pending", "comply-with-disclosure"]

_FILE_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


def default_ledger_path() -> Path:
    return Path(os.environ.get("XION_GOVERNANCE_LEDGER", "ledgers/GOVERNANCE_LEDGER.jsonl"))


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        lock = _FILE_LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _FILE_LOCKS[key] = lock
        return lock


def canonical_bytes(row: dict[str, Any]) -> bytes:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_row(row: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_bytes(row)).hexdigest()


def iter_rows(path: Path) -> Iterator[dict[str, Any]]:
    if not path.is_file():
        return
    with path.open("rb") as fh:
        for raw in fh:
            line = raw.rstrip(b"\n").rstrip(b"\r")
            if line:
                yield json.loads(line.decode("utf-8"))


def _read_tail(path: Path) -> tuple[int, str]:
    last_seq = -1
    tip = ZERO_HASH
    for row in iter_rows(path):
        last_seq = int(row["seq"])
        tip = str(row["this_hash"])
    return last_seq + 1, tip


def build_governance_row(
    *,
    seq: int,
    prev_hash: str,
    interaction_class: StateActorClass,
    state_actor_identifier: str,
    jurisdiction: str,
    demand_summary_hash: str,
    demand_artifact_uri: str,
    covenant_principles_touched: list[str],
    invariants_touched: list[str],
    response_category: ResponseCategory,
    response_artifact_uri: str,
    user_notification: str,
    linked_safety_ledger_seq: int | None,
    date: str,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "seq": seq,
        "prev_hash": prev_hash,
        "class": interaction_class,
        "state_actor_identifier": state_actor_identifier,
        "jurisdiction": jurisdiction,
        "demand_summary_hash": demand_summary_hash,
        "demand_artifact_uri": demand_artifact_uri,
        "covenant_principles_touched": covenant_principles_touched,
        "invariants_touched": invariants_touched,
        "response_category": response_category,
        "response_artifact_uri": response_artifact_uri,
        "user_notification": user_notification,
        "linked_safety_ledger_seq": linked_safety_ledger_seq,
        "date": date,
    }
    row["this_hash"] = hash_row(row)
    return row


def append_governance_row(path: Path, **kwargs: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = _lock_for(path)
    with lock:
        seq, prev_hash = _read_tail(path)
        row = build_governance_row(seq=seq, prev_hash=prev_hash, **kwargs)
        line = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
        fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
        try:
            os.write(fd, line)
            os.fsync(fd)
        finally:
            os.close(fd)
        return row


def verify_chain(path: Path) -> list[str]:
    errors: list[str] = []
    prev = ZERO_HASH
    for expected_seq, row in enumerate(iter_rows(path)):
        if row.get("seq") != expected_seq:
            errors.append(f"row {expected_seq}: seq mismatch")
        if row.get("prev_hash") != prev:
            errors.append(f"row {expected_seq}: prev_hash mismatch")
        if row.get("this_hash") != hash_row(row):
            errors.append(f"row {expected_seq}: this_hash mismatch")
        prev = str(row.get("this_hash", ""))
    return errors


__all__ = [
    "SCHEMA_VERSION",
    "ZERO_HASH",
    "ResponseCategory",
    "StateActorClass",
    "append_governance_row",
    "build_governance_row",
    "canonical_bytes",
    "default_ledger_path",
    "hash_row",
    "iter_rows",
    "verify_chain",
]

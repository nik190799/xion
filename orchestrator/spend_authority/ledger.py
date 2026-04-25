"""SPEND_AUTHORITY_LEDGER append-only hash-chain writer."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
ZERO_HASH = "0" * 64
SOURCE_SHA256 = "45b0ca69ff2865779d46dfe9eb45c8f7a2146974404d00eb087264d36acc173e"

POSTURES = frozenset(
    {
        "S1_operator_all",
        "S2_operator_strategic",
        "S3_operator_burn_envelope",
        "S4_governance_strategic",
        "S5_self_sovereign_inside_fence",
    }
)
MODES = frozenset({"survival", "baseline", "acceleration", "expansion"})
APPROVERS = frozenset({"operator", "ao_core", "governance", "xion"})
DECISIONS = frozenset({"approved", "rejected", "escalated"})
SPEND_CLASSES = frozenset(
    {
        "survival_ops",
        "routine_ops",
        "one_time_acceleration",
        "recurring_capacity",
        "posture_transition",
        "contested_headroom",
    }
)

_LOCKS: dict[str, threading.Lock] = {}
_REGISTRY_LOCK = threading.Lock()


@dataclass(frozen=True)
class SpendAuthorityRecord:
    decision_id: str
    spend_class: str
    active_posture: str
    active_mode: str
    approver_class: str
    authority_decision: str
    evidence_bundle_hash: str
    inflow_tag_reference: str
    fund_source: str
    runway_measurements: dict[str, float]
    proposed_amount: float
    recurring_burn_weekly_delta: float = 0.0
    timestamp_utc_ns: int = field(default_factory=time.time_ns)

    def __post_init__(self) -> None:
        _require(self.decision_id, "decision_id")
        _require_in(self.spend_class, SPEND_CLASSES, "spend_class")
        _require_in(self.active_posture, POSTURES, "active_posture")
        _require_in(self.active_mode, MODES, "active_mode")
        _require_in(self.approver_class, APPROVERS, "approver_class")
        _require_in(self.authority_decision, DECISIONS, "authority_decision")
        _require(self.evidence_bundle_hash, "evidence_bundle_hash")
        _require(self.fund_source, "fund_source")
        if self.proposed_amount < 0:
            raise ValueError("proposed_amount must be non-negative")
        if self.recurring_burn_weekly_delta < 0:
            raise ValueError("recurring_burn_weekly_delta must be non-negative")


def append(path: Path | str, record: SpendAuthorityRecord) -> dict[str, Any]:
    ledger_path = Path(path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    with _lock_for(ledger_path):
        rows = list(iter_rows(ledger_path))
        prev_hash = rows[-1]["this_hash"] if rows else ZERO_HASH
        row = {
            "schema_version": SCHEMA_VERSION,
            "seq": len(rows),
            "prev_hash": prev_hash,
            "this_hash": "",
            "source_sha256": SOURCE_SHA256,
            **asdict(record),
        }
        row["this_hash"] = _hash_row(row)
        with ledger_path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
        return row


def iter_rows(path: Path | str) -> Iterator[dict[str, Any]]:
    ledger_path = Path(path)
    if not ledger_path.is_file():
        return
    with ledger_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def verify_chain(path: Path | str) -> list[str]:
    errors: list[str] = []
    prev_hash = ZERO_HASH
    seen_ids: set[str] = set()
    for expected_seq, row in enumerate(iter_rows(path)):
        missing = _required_fields() - row.keys()
        if missing:
            errors.append(f"row {expected_seq}: missing fields {sorted(missing)}")
            continue
        if row["seq"] != expected_seq:
            errors.append(f"row {expected_seq}: seq mismatch {row['seq']!r}")
        if row["prev_hash"] != prev_hash:
            errors.append(f"row {expected_seq}: prev_hash mismatch")
        if row["this_hash"] != _hash_row(row):
            errors.append(f"row {expected_seq}: this_hash mismatch")
        if row["decision_id"] in seen_ids:
            errors.append(f"row {expected_seq}: duplicate decision_id {row['decision_id']!r}")
        seen_ids.add(row["decision_id"])
        with _validation_context(row, expected_seq, errors):
            _validate_row(row, expected_seq, errors)
        prev_hash = row["this_hash"]
    return errors


def _validate_row(row: dict[str, Any], seq: int, errors: list[str]) -> None:
    for key, allowed in (
        ("active_posture", POSTURES),
        ("active_mode", MODES),
        ("approver_class", APPROVERS),
        ("authority_decision", DECISIONS),
        ("spend_class", SPEND_CLASSES),
    ):
        if row[key] not in allowed:
            errors.append(f"row {seq}: invalid {key} {row[key]!r}")
    if row["source_sha256"] != SOURCE_SHA256:
        errors.append(f"row {seq}: source_sha256 mismatch")


class _validation_context:
    def __init__(self, row: dict[str, Any], seq: int, errors: list[str]) -> None:
        self._row = row
        self._seq = seq
        self._errors = errors

    def __enter__(self) -> None:
        return None

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc is not None:
            self._errors.append(f"row {self._seq}: validation exception: {exc}")
            return True
        return False


def _required_fields() -> set[str]:
    return {
        "schema_version",
        "seq",
        "prev_hash",
        "this_hash",
        "timestamp_utc_ns",
        "decision_id",
        "spend_class",
        "active_posture",
        "active_mode",
        "approver_class",
        "authority_decision",
        "evidence_bundle_hash",
        "inflow_tag_reference",
        "fund_source",
        "runway_measurements",
        "proposed_amount",
        "recurring_burn_weekly_delta",
        "source_sha256",
    }


def _hash_row(row: dict[str, Any]) -> str:
    body = {key: value for key, value in row.items() if key != "this_hash"}
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _lock_for(path: Path) -> threading.Lock:
    key = str(path.resolve())
    with _REGISTRY_LOCK:
        lock = _LOCKS.get(key)
        if lock is None:
            lock = threading.Lock()
            _LOCKS[key] = lock
        return lock


def _require(value: str, name: str) -> None:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty string")


def _require_in(value: str, allowed: frozenset[str], name: str) -> None:
    if value not in allowed:
        raise ValueError(f"{name} must be one of {sorted(allowed)}, got {value!r}")


__all__ = ["SpendAuthorityRecord", "append", "iter_rows", "verify_chain"]

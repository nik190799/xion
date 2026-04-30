from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal


RegistryEvent = Literal["attestation", "disavowal"]


@dataclass(frozen=True)
class VesselRegistryRow:
    schema_version: int
    seq: int
    event: RegistryEvent
    vessel_id: str
    compact_sha256: str
    artifact_path: str
    attested_at_utc: str
    prev_hash: str
    row_hash: str
    not_approval_gate: bool = True


def _canonical(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _row_hash(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("row_hash", None)
    return hashlib.sha256(_canonical(unsigned).encode("utf-8")).hexdigest()


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rows.append(json.loads(line))
    return rows


def _append(path: Path, event: RegistryEvent, vessel_id: str, compact_path: Path) -> VesselRegistryRow:
    rows = _read_rows(path)
    seq = len(rows) + 1
    prev_hash = rows[-1].get("row_hash", "") if rows else ""
    compact_sha256 = hashlib.sha256(compact_path.read_bytes()).hexdigest()
    payload: dict[str, Any] = {
        "schema_version": 1,
        "seq": seq,
        "event": event,
        "vessel_id": vessel_id,
        "compact_sha256": compact_sha256,
        "artifact_path": compact_path.as_posix(),
        "attested_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "prev_hash": prev_hash,
        "not_approval_gate": True,
    }
    payload["row_hash"] = _row_hash(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(_canonical(payload) + "\n")
    return VesselRegistryRow(**payload)


def append_attestation(path: Path, vessel_id: str, compact_path: Path) -> VesselRegistryRow:
    return _append(path, "attestation", vessel_id, compact_path)


def append_disavowal(path: Path, vessel_id: str, compact_path: Path) -> VesselRegistryRow:
    return _append(path, "disavowal", vessel_id, compact_path)


def verify_registry(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        rows = _read_rows(path)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [f"vessel registry unreadable: {exc}"]
    prev_hash = ""
    for idx, row in enumerate(rows, start=1):
        for field in (
            "schema_version",
            "seq",
            "event",
            "vessel_id",
            "compact_sha256",
            "artifact_path",
            "attested_at_utc",
            "prev_hash",
            "row_hash",
            "not_approval_gate",
        ):
            if field not in row:
                errors.append(f"row {idx}: missing field {field}")
        if row.get("seq") != idx:
            errors.append(f"row {idx}: seq must be {idx}")
        if row.get("event") not in {"attestation", "disavowal"}:
            errors.append(f"row {idx}: invalid event {row.get('event')!r}")
        if row.get("not_approval_gate") is not True:
            errors.append(f"row {idx}: not_approval_gate must be true")
        if row.get("prev_hash") != prev_hash:
            errors.append(f"row {idx}: prev_hash mismatch")
        if row.get("row_hash") != _row_hash(row):
            errors.append(f"row {idx}: row_hash mismatch")
        prev_hash = str(row.get("row_hash", ""))
    return errors

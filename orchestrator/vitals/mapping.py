"""Signal-to-vital mapping doctrine (Phase 6.4.b).

Every sealed domain is a reduced aggregate of named ``Signal`` kinds on the
:class:`~orchestrator.signals.bus.SignalBus`.  Adding a new receptor kind and
wiring it here (one row) extends the vital without editing aggregate code
elsewhere.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from orchestrator.signals.bus import SignalBus

MappingEntry = Union["list[SignalDep]", Literal["not_yet_sealed"]]


@dataclass(frozen=True)
class SignalDep:
    kind: str
    weight: float = 1.0
    invert: bool = False


# NOTE: keep kinds aligned with `orchestrator/signals/schema.py` registrations.
VITAL_MAPPING: dict[str, list[SignalDep] | str] = {
    "Financial Vitality": [
        SignalDep("interoception.cost_pressure", weight=0.5, invert=True),
        SignalDep("resource.cost_runway_days", weight=0.5, invert=False),
    ],
    "Substrate Vitality": [
        SignalDep("proprioception.relay_health", weight=0.25),
        SignalDep("proprioception.arbiter_health", weight=0.25),
        SignalDep("connection.ao_core_health", weight=0.25),
        SignalDep("resource.disk_remaining_pct", weight=0.25),
    ],
    "Constitutional Integrity": [
        SignalDep("topography.soul_prompt_sha_drift", weight=0.34, invert=True),
        SignalDep("chronoception.time_in_degraded_mode_s", weight=0.33, invert=True),
        SignalDep("topography.constitution_doc_hash_drift", weight=0.33, invert=True),
    ],
    "Behavioral Fidelity": "not_yet_sealed",
    "Relational Trust": "not_yet_sealed",
    "Service Usefulness": "not_yet_sealed",
    "Evolutionary Health": "not_yet_sealed",
    "Structural Decentralization": "not_yet_sealed",
}

_PATH = Path(__file__).resolve()


def _file_sha256() -> str:
    data = _PATH.read_bytes()
    return hashlib.sha256(data).hexdigest()


VITAL_MAPPING_METHODOLOGY_SHA256: str = _file_sha256()


def _coerce_01_for_kind(kind: str, sig_val: Any) -> float:
    if isinstance(sig_val, bool):
        return 1.0 if sig_val else 0.0
    if not isinstance(sig_val, (int, float)):
        return 0.5
    v = float(sig_val)
    if kind == "resource.cost_runway_days":
        return min(1.0, max(0.0, v / 400.0))
    if 0.0 <= v <= 1.0:
        return v
    # e.g. seconds of staleness
    return max(0.0, min(1.0, 1.0 - min(1.0, v / (7 * 24 * 3600.0))))


def aggregate_domain(
    domain: str,
    bus: "SignalBus",
) -> tuple[float, str] | None:
    """Return (reading 0..1, band) or None if this domain is not_sealed in mapping."""
    spec = VITAL_MAPPING.get(domain)
    if spec == "not_yet_sealed" or spec is None:
        return None
    if not isinstance(spec, list):
        return None
    wsum = 0.0
    acc = 0.0
    for dep in spec:
        s = bus.latest(dep.kind)
        if s is None:
            continue
        v = _coerce_01_for_kind(dep.kind, s.value)
        if dep.invert:
            v = 1.0 - v
        acc += v * dep.weight
        wsum += dep.weight
    if wsum == 0.0:
        return None
    reading = acc / wsum
    if reading > 0.6:
        band = "healthy"
    elif reading > 0.3:
        band = "warning"
    else:
        band = "critical"
    return reading, band

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from orchestrator.signals.envelope import Signal


class SignalSchemaError(Exception):
    """Raised when a signal fails schema validation."""


@dataclass(frozen=True)
class SignalSchema:
    kind: str
    value_type: str  # "float" | "bool" | "int" | "str" | "dict" | "any"
    min_value: float | None
    max_value: float | None
    version: int


REGISTRY: dict[str, SignalSchema] = {}


def register_kind(schema: SignalSchema) -> None:
    REGISTRY[schema.kind] = schema


def _type_ok(v: Any, t: str) -> bool:
    if t == "any":
        return True
    if t == "float":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    if t == "int":
        return type(v) is int  # exclude bool
    if t == "bool":
        return isinstance(v, bool)
    if t == "str":
        return isinstance(v, str)
    if t == "dict":
        return isinstance(v, dict)
    return False


def validate_signal(s: Signal) -> None:
    sc = REGISTRY.get(s.kind)
    if sc is None:
        raise SignalSchemaError(f"unknown kind {s.kind!r}")
    if s.schema_version != sc.version:
        raise SignalSchemaError(
            f"schema_version mismatch for {s.kind!r}: got {s.schema_version}, want {sc.version}"
        )
    if not _type_ok(s.value, sc.value_type):
        raise SignalSchemaError(
            f"value type for {s.kind!r} must be {sc.value_type}, got {type(s.value).__name__}"
        )
    if sc.value_type in ("float", "int") and sc.min_value is not None and sc.max_value is not None:
        fv = float(s.value)
        if not (sc.min_value <= fv <= sc.max_value):
            raise SignalSchemaError(
                f"value {fv} out of range for {s.kind!r} ({sc.min_value}..{sc.max_value})"
            )


# --- Pre-registered kinds for the four legacy senses (Phase 5c) ---

METHOLOGY_INFERRED = "0000000000000000000000000000000000000000000000000000000000000000"
METHOLOGY_DERIVED = "1111111111111111111111111111111111111111111111111111111111111111"

register_kind(
    SignalSchema("interoception.cost_pressure", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("interoception.survival_pressure", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("interoception.treasury_stress", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("interoception.memory_pressure", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("chronoception.monotonic_drift_ns", "int", -1e20, 1e20, 1)
)
register_kind(
    SignalSchema("chronoception.checkpoint_staleness_s", "float", 0.0, 1e9, 1)
)
register_kind(
    SignalSchema("chronoception.time_in_degraded_mode_s", "float", 0.0, 1e9, 1)
)
register_kind(SignalSchema("proprioception.relay_health", "bool", None, None, 1))
register_kind(SignalSchema("proprioception.arbiter_health", "bool", None, None, 1))
register_kind(
    SignalSchema("proprioception.watchdog_fires", "int", 0, 1_000_000, 1)
)
register_kind(
    SignalSchema("distress.text_distress", "float", 0.0, 1.0, 1)
)
# Infrastructure / health
register_kind(
    SignalSchema("vital.bus_integrity", "str", None, None, 1)
)
# Mapping doctrine resource / connection kinds (v1)
register_kind(SignalSchema("resource.cost_runway_days", "float", 0.0, 1e6, 1))
register_kind(
    SignalSchema("resource.disk_remaining_pct", "float", 0.0, 1.0, 1)
)
register_kind(SignalSchema("connection.ao_core_health", "bool", None, None, 1))
register_kind(
    SignalSchema("topography.soul_prompt_sha_drift", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("topography.constitution_doc_hash_drift", "float", 0.0, 1.0, 1)
)
# Governance
register_kind(
    SignalSchema("governance.consent_change", "dict", None, None, 1)
)
# Topography (Phase 6.4.b) — `str` / `int` for self-knowledge
register_kind(
    SignalSchema("topography.worker_id", "str", None, None, 1)
)
register_kind(
    SignalSchema("topography.host", "str", None, None, 1)
)
register_kind(
    SignalSchema("topography.pid", "int", 0, 50_000_000, 1)
)
register_kind(
    SignalSchema("topography.lineage_hash", "str", None, None, 1)
)
register_kind(
    SignalSchema("topography.soul_prompt_sha_drift", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("topography.constitution_doc_hash_drift", "float", 0.0, 1.0, 1)
)
register_kind(
    SignalSchema("inference.provider_floor_count", "int", 0, 1_000, 1)
)

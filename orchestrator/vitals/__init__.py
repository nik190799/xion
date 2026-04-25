"""Vital Signs (eight-domain composite) package.

Implements the eight domains from docs/22-VITAL-SIGNS.md.  Sealed domains
(Phase 6.4.b) read from :class:`~orchestrator.signals.bus.SignalBus` via
``vitals/mapping.py`` when the bus carries sufficient signals; otherwise the
legacy :func:`orchestrator.senses.vitals_emitter._compute_vitals` path from
``SensoriumState`` is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from orchestrator.sensorium import SensoriumState
    from orchestrator.signals.bus import SignalBus

Band = Literal["healthy", "warning", "critical", "not_yet_sealed"]


@dataclass(frozen=True)
class VitalDomain:
    name: str
    band: Band
    reading: float | str | None
    methodology_sha256: str
    subjective: bool


_SEALED = (
    "Financial Vitality",
    "Substrate Vitality",
    "Constitutional Integrity",
)
_LEGACY_LABEL = {
    "Financial Vitality": "1 — Financial Vitality",
    "Substrate Vitality": "2 — Substrate Vitality",
    "Constitutional Integrity": "3 — Constitutional Integrity",
}


def get_composite_vitals(
    *,
    bus: "SignalBus | None" = None,
    state: "SensoriumState | None" = None,
) -> list[VitalDomain]:
    from orchestrator.senses.vitals_emitter import _compute_vitals
    from orchestrator.vitals.mapping import (
        VITAL_MAPPING_METHODOLOGY_SHA256,
        aggregate_domain,
    )

    if state is None:
        from orchestrator.sensorium import (
            Chronoception,
            DistressSignal,
            Interoception,
            Proprioception,
            SensoriumState,
        )
        import time

        state = SensoriumState(
            interoception=Interoception(
                survival_pressure=0.0, treasury_stress=0.0, cost_pressure=0.0, as_of_utc_ns=0
            ),
            chronoception=Chronoception.from_ticks(
                last_checkpoint_utc_ns=None,
                now_utc_ns=0,
                degraded_since_utc_ns=None,
                monotonic_drift_ns=0,
            ),
            proprioception=Proprioception.from_runtime(
                relay_healthy=True,
                arbiter_healthy=True,
                watchdog_fires_recent=0,
                as_of_utc_ns=0,
            ),
            distress=DistressSignal(0.0, "textual", 0),
            as_of_utc_ns=time.time_ns(),
        )

    live = {v["domain"]: v for v in _compute_vitals(state)}

    out: list[VitalDomain] = []
    for name in _SEALED:
        if bus is not None:
            agg = aggregate_domain(name, bus)
            if agg is not None:
                reading, band = agg
                out.append(
                    VitalDomain(
                        name=name,
                        band=band,  # type: ignore[assignment]
                        reading=reading,
                        methodology_sha256=VITAL_MAPPING_METHODOLOGY_SHA256,
                        subjective=False,
                    )
                )
                continue
        legacy = _LEGACY_LABEL[name]
        v = live[legacy]
        out.append(
            VitalDomain(
                name=name,
                band=v["band"],
                reading=v["reading"],
                methodology_sha256=v["methodology_sha256"],
                subjective=v["subjective"],
            )
        )

    out.extend(
        [
            VitalDomain(
                name="Behavioral Fidelity",
                band="not_yet_sealed",
                reading=None,
                methodology_sha256="pending",
                subjective=False,
            ),
            VitalDomain(
                name="Relational Trust",
                band="not_yet_sealed",
                reading=None,
                methodology_sha256="pending",
                subjective=True,
            ),
            VitalDomain(
                name="Service Usefulness",
                band="not_yet_sealed",
                reading=None,
                methodology_sha256="pending",
                subjective=False,
            ),
            VitalDomain(
                name="Evolutionary Health",
                band="not_yet_sealed",
                reading=None,
                methodology_sha256="pending",
                subjective=False,
            ),
            VitalDomain(
                name="Structural Decentralization",
                band="not_yet_sealed",
                reading=None,
                methodology_sha256="pending",
                subjective=False,
            ),
        ]
    )
    return out

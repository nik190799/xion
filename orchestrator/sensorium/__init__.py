"""Sensorium: parallel senses feeding Volition and the Arbiter's
Principle-10 OR-combination. Phase 5c code surface: four live internal
senses (Interoception, Chronoception, Proprioception, DistressSignal)
plus the SENSORIUM_LEDGER append-only hash-chained record. The eight
exterocept families remain `"stub"`-string placeholders in
`Sensorium.tick()` until Phase 6+.
"""

from orchestrator.sensorium.sensorium import (
    DISTRESS_THRESHOLD,
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SenseName,
    Sensorium,
    SensoriumState,
)

__all__ = [
    "Chronoception",
    "DISTRESS_THRESHOLD",
    "DistressSignal",
    "Interoception",
    "Proprioception",
    "SenseName",
    "Sensorium",
    "SensoriumState",
]

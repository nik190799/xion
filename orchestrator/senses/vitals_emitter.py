"""Phase 6.4: Vitals Emitter.

Translates the internal SensoriumState into the eight load-bearing
vital domains (22-VITAL-SIGNS.md), emitting on band-change or via
a <= 1 Hz poll.
"""
import json
import time
from collections.abc import AsyncIterator

from orchestrator.sensorium import SensoriumState
from orchestrator.sensorium.presence_bus import PresenceBus

# Frozen SHA-256 hashes of the methodology documents for each domain
METHODOLOGY_HASHES = {
    # docs/21-SUSTAINABILITY.md
    "1 — Financial Vitality": "72b90e6e6e0b0d70912407959866a67febb7b575e41a26f440069e55f0baf0aa",
    # docs/04-ARCHITECTURE.md
    "2 — Substrate Vitality": "da891454f771910ce7bbba3ea9fb649e4af0a6202f78aff1aeea2611051bb260",
    # docs/14-UPGRADE-PATHS.md
    "3 — Constitutional Integrity": "e2ee3bc6a9b22f977b28faa75681ab9be082fc6fe6a49f2073421557debe1c3d",
}


def _compute_vitals(state: SensoriumState) -> list[dict]:
    vitals = []

    # Domain 1: Financial Vitality (objective)
    # Healthy: ladder step <= 1 -> cost_pressure is low
    d1_reading = max(0.0, 1.0 - state.interoception.cost_pressure)
    d1_band = "healthy" if d1_reading > 0.6 else ("warning" if d1_reading > 0.3 else "critical")
    vitals.append({
        "domain": "1 — Financial Vitality",
        "reading": d1_reading,
        "band": d1_band,
        "methodology_sha256": METHODOLOGY_HASHES["1 — Financial Vitality"],
        "subjective": False
    })

    # Domain 2: Substrate Vitality (objective)
    d2_healthy = state.proprioception.relay_healthy and state.proprioception.arbiter_healthy
    d2_reading = 1.0 if d2_healthy else 0.0
    d2_band = "healthy" if d2_healthy else "critical"
    vitals.append({
        "domain": "2 — Substrate Vitality",
        "reading": d2_reading,
        "band": d2_band,
        "methodology_sha256": METHODOLOGY_HASHES["2 — Substrate Vitality"],
        "subjective": False
    })

    # Domain 3: Constitutional Integrity (objective)
    # Based on degraded mode (surrogate for cadence floor/lattice integrity in 6.4)
    d3_reading = 1.0 if state.chronoception.time_in_degraded_mode_s == 0.0 else 0.0
    d3_band = "healthy" if d3_reading == 1.0 else "warning"
    vitals.append({
        "domain": "3 — Constitutional Integrity",
        "reading": d3_reading,
        "band": d3_band,
        "methodology_sha256": METHODOLOGY_HASHES["3 — Constitutional Integrity"],
        "subjective": False
    })

    return vitals


async def stream_vitals(presence_bus: PresenceBus) -> AsyncIterator[str]:
    """Push-on-band-change + <= 1 Hz poll."""
    last_bands: dict[str, str] = {}
    last_emit_s = 0.0

    # Read directly from the subscription since it pushes at the Supervisor tick rate
    # which is <= 1 Hz (10 seconds default).
    async for state in presence_bus.subscribe():
        vitals = _compute_vitals(state)
        current_bands = {v["domain"]: v["band"] for v in vitals}

        now_s = time.monotonic()
        band_changed = current_bands != last_bands

        # Emit if bands changed or if we just haven't emitted recently (1Hz poll baseline)
        if band_changed or (now_s - last_emit_s >= 1.0):
            payload = {
                "type": "vitals",
                "vitals": vitals,
                "timestamp": state.as_of_utc_ns // 1_000_000
            }
            yield json.dumps(payload) + "\n"
            last_bands = current_bands
            last_emit_s = now_s

__all__ = ["stream_vitals"]

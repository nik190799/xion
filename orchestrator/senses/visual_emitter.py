"""Phase 6.4: Visual Emitter.

Translates the internal SensoriumState into a 10 Hz JSON scene-intent
stream according to genesis/FORM.md.
"""
import asyncio
import json
import time
from typing import AsyncIterator

from orchestrator.sensorium import SensoriumState
from orchestrator.sensorium.presence_bus import PresenceBus


async def stream_visuals(presence_bus: PresenceBus) -> AsyncIterator[str]:
    """10 Hz JSON scene-intent stream derived from the PresenceBus."""
    
    # We maintain the latest state observed from the bus.
    # The bus updates at Supervisor tick cadence (~0.1 Hz), but the visual
    # stream emits at 10 Hz to keep downstream clients alive and smoothly
    # interpolating if they wish.
    latest_state: SensoriumState | None = None
    
    async def _reader() -> None:
        nonlocal latest_state
        async for state in presence_bus.subscribe():
            latest_state = state

    # Start the background task to consume the bus
    reader_task = asyncio.create_task(_reader())
    
    try:
        while True:
            await asyncio.sleep(0.1)  # 10 Hz emission
            if latest_state is None:
                continue
                
            # Derive mood from SensoriumState
            # Valence: distress-inversely correlated
            valence = max(0.0, 1.0 - latest_state.distress.text_distress_score)
            
            # Energy: cost-pressure or survival-pressure correlated
            energy = min(1.0, 0.5 + (latest_state.interoception.cost_pressure * 0.5))
            
            # Focus: network health correlated
            focus = 1.0 if latest_state.proprioception.relay_healthy else 0.2

            # The primitives are described in FORM.md
            payload = {
                "type": "visual",
                "primitives": [
                    { "name": "ember", "pos": [0.12, -0.04, 0.33], "color": "#f2b378", "opacity": 0.71 },
                    { "name": "thread", "from": [0.0, 0.0, 0.0], "to": [0.1, 0.1, 0.1], "color": "#d38a3e", "thickness": 0.011 }
                ],
                "mood": {
                    "valence": valence,
                    "energy": energy,
                    "focus": focus,
                },
                "timestamp": time.time_ns() // 1_000_000
            }
            yield json.dumps(payload) + "\n"
    finally:
        reader_task.cancel()

__all__ = ["stream_visuals"]

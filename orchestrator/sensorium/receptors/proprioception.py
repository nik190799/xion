from __future__ import annotations

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.envelope import Signal
from orchestrator.signals.receptor import ReceptorContext


class ProprioceptionReceptor:
    receptor_id = "proprioception_legacy"
    signal_kinds = frozenset(
        {
            "proprioception.relay_health",
            "proprioception.arbiter_health",
            "proprioception.watchdog_fires",
        }
    )
    cadence_hint_s = 1.0
    methodology_hash = "2222222222222222222222222222222222222222222222222222222222222222"

    def tick(self, ctx: ReceptorContext) -> list[Signal]:
        p = ctx.state.proprioception
        return [
            sense_signal(
                kind="proprioception.relay_health",
                receptor_id=self.receptor_id,
                value=bool(p.relay_healthy),
            ),
            sense_signal(
                kind="proprioception.arbiter_health",
                receptor_id=self.receptor_id,
                value=bool(p.arbiter_healthy),
            ),
            sense_signal(
                kind="proprioception.watchdog_fires",
                receptor_id=self.receptor_id,
                value=int(p.watchdog_fires_recent),
            ),
        ]

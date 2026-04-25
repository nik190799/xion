from __future__ import annotations

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.envelope import Signal
from orchestrator.signals.receptor import ReceptorContext


class ChronoceptionReceptor:
    receptor_id = "chronoception_legacy"
    signal_kinds = frozenset(
        {
            "chronoception.monotonic_drift_ns",
            "chronoception.checkpoint_staleness_s",
            "chronoception.time_in_degraded_mode_s",
        }
    )
    cadence_hint_s = 1.0
    methodology_hash = "2222222222222222222222222222222222222222222222222222222222222222"

    def tick(self, ctx: ReceptorContext) -> list[Signal]:
        c = ctx.state.chronoception
        return [
            sense_signal(
                kind="chronoception.monotonic_drift_ns",
                receptor_id=self.receptor_id,
                value=int(c.monotonic_drift_ns),
            ),
            sense_signal(
                kind="chronoception.checkpoint_staleness_s",
                receptor_id=self.receptor_id,
                value=float(c.checkpoint_staleness_s),
            ),
            sense_signal(
                kind="chronoception.time_in_degraded_mode_s",
                receptor_id=self.receptor_id,
                value=float(c.time_in_degraded_mode_s),
            ),
        ]

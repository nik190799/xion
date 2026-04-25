from __future__ import annotations

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.envelope import Signal
from orchestrator.signals.receptor import ReceptorContext


class DistressReceptor:
    receptor_id = "distress_legacy"
    signal_kinds = frozenset({"distress.text_distress"})
    cadence_hint_s = 1.0
    methodology_hash = "2222222222222222222222222222222222222222222222222222222222222222"

    def tick(self, ctx: ReceptorContext) -> list[Signal]:
        d = ctx.state.distress
        return [
            sense_signal(
                kind="distress.text_distress",
                receptor_id=self.receptor_id,
                value=float(d.text_distress_score),
            ),
        ]

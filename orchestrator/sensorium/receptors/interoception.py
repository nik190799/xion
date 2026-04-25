from __future__ import annotations

from orchestrator.sensorium.receptors._util import sense_signal
from orchestrator.signals.envelope import Signal
from orchestrator.signals.receptor import ReceptorContext

_MEM = 0.0  # not yet live


class InteroceptionCostPressure:
    receptor_id = "interoception_legacy"
    signal_kinds = frozenset(
        {
            "interoception.cost_pressure",
            "interoception.survival_pressure",
            "interoception.treasury_stress",
            "interoception.memory_pressure",
        }
    )
    cadence_hint_s = 1.0
    methodology_hash = "2222222222222222222222222222222222222222222222222222222222222222"

    def tick(self, ctx: ReceptorContext) -> list[Signal]:
        i = ctx.state.interoception
        return [
            sense_signal(
                kind="interoception.cost_pressure",
                receptor_id=self.receptor_id,
                value=float(i.cost_pressure),
            ),
            sense_signal(
                kind="interoception.survival_pressure",
                receptor_id=self.receptor_id,
                value=float(i.survival_pressure),
            ),
            sense_signal(
                kind="interoception.treasury_stress",
                receptor_id=self.receptor_id,
                value=float(i.treasury_stress),
            ),
            sense_signal(
                kind="interoception.memory_pressure",
                receptor_id=self.receptor_id,
                value=_MEM,
            ),
        ]

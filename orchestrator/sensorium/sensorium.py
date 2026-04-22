"""Sensorium (Phase 5 skeleton) — exteroception toward Interoception.

`docs/05-SENSORIUM.md` is canonical. This module only lands the
structural hook: a single interocept reading (`survival_pressure`) derived
from cost / runway placeholders until Treasury + Relay vitals are wired.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any


class SenseName(str, Enum):
    """The eight exterocept families (others stubbed on first landing)."""

    SOCIAL = "social"
    CRYPTOCEPTION = "cryptoception"
    CIVIC = "civic"
    ECOS = "ecos"
    TERRITORY = "territory"
    REGULATORY = "regulatory"
    TREASURY = "treasury"
    CULTUURAL = "cultural"
    # Interoception is the ninth, internal, sense — not a member of
    # the exterocept ring but emitted alongside it in `Sensorium.tick`.
    INTEROCEPTION = "interoception"


@dataclass
class Interoception:
    """Internal pressure: cost vs runway, scaled to [0,1] for volition.

    The formula is a placeholder. Phase 5+ will replace `treasury_stress`
    and `cost_pressure` with readouts from real ledgers. What is
    load-bearing *today* is: there exists a `survival_pressure` scalar
    the Supervisor can read without hand-waving.
    """

    survival_pressure: float
    """0.0 = comfortable; 1.0 = critical. Saturated, not linear."""

    treasury_stress: float = 0.0
    cost_pressure: float = 0.0
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    @staticmethod
    def from_placeholders(
        *, treasury_stress: float, cost_pressure: float
    ) -> "Interoception":
        t = max(0.0, min(1.0, float(treasury_stress)))
        c = max(0.0, min(1.0, float(cost_pressure)))
        surv = max(t, c)
        return Interoception(
            survival_pressure=surv,
            treasury_stress=t,
            cost_pressure=c,
        )


@dataclass
class Sensorium:
    """Aggregates the senses. Non-interoception channels are stubbed."""

    _intero: Interoception = field(
        default_factory=lambda: Interoception.from_placeholders(
            treasury_stress=0.0, cost_pressure=0.0
        )
    )

    def set_interoception(self, i: Interoception) -> None:
        self._intero = i

    def tick(self) -> dict[str, Any]:
        """One fusion tick. Returns a JSON-serialisable dict for logs."""
        return {
            "t": time.time_ns(),
            "senses": {s.value: "stub" for s in SenseName if s != SenseName.INTEROCEPTION},
            "interoception": {
                "survival_pressure": self._intero.survival_pressure,
                "treasury_stress": self._intero.treasury_stress,
                "cost_pressure": self._intero.cost_pressure,
                "as_of_utc_ns": self._intero.as_of_utc_ns,
            },
        }


__all__ = [
    "Interoception",
    "SenseName",
    "Sensorium",
]

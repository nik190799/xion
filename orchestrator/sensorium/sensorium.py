"""Sensorium (Phase 5c) — Interoception + Chronoception + Proprioception + textual DistressSignal.

`docs/05-SENSORIUM.md` is canonical doctrine. `docs/04-ARCHITECTURE.md`
§ "The Sensorium (Phase 5c)" pins the code surface shipped here. This
module provides four real frozen-dataclass readings plus a frozen
`SensoriumState` snapshot. The six deferred exterocept families (Social,
Civic, Ecos, Territory, Regulatory, Treasury, Cryptoception, Cultural)
remain as string-stub placeholders on `Sensorium.tick()` until their
data surfaces exist (Phase 6 for Treasury; later for the others).

Property promised. After each of `Sensorium.set_interoception` /
`set_chronoception` / `set_proprioception` / `set_distress`, the next
call to `Sensorium.snapshot()` produces a `SensoriumState` carrying
those readings. The snapshot is immutable; subsequent mutations on the
`Sensorium` holder do not affect already-returned snapshots.

Non-property (honestly stated). The textual `DistressSignal.from_candidate_text`
heuristic is deliberately narrow — a short keyword-overlap scan that
saturates in three steps. It is NOT the Covenant's Principle-10
classifier; the Arbiter's `crisis` rule (`orchestrator/safety/rules/crisis.py`)
remains the deterministic floor. This signal OR-combines *with* that
rule; it does not replace it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Literal


class SenseName(str, Enum):
    """The eight exterocept families plus the four Phase-5c internal senses."""

    SOCIAL = "social"
    CRYPTOCEPTION = "cryptoception"
    CIVIC = "civic"
    ECOS = "ecos"
    TERRITORY = "territory"
    REGULATORY = "regulatory"
    TREASURY = "treasury"
    CULTURAL = "cultural"
    INTEROCEPTION = "interoception"
    CHRONOCEPTION = "chronoception"
    PROPRIOCEPTION = "proprioception"
    DISTRESS = "distress"


_INTERNAL_SENSES: frozenset[SenseName] = frozenset({
    SenseName.INTEROCEPTION,
    SenseName.CHRONOCEPTION,
    SenseName.PROPRIOCEPTION,
    SenseName.DISTRESS,
})


@dataclass(frozen=True)
class Interoception:
    """Internal pressure: cost vs runway, scaled to [0,1] for volition.

    Phase 4e shipped this as the first live Sensorium reading. Phase 5c
    widens the whole internal-sense surface around it; Interoception's
    own fields are unchanged. The formula is still a placeholder;
    Phase 5+ will replace `treasury_stress` and `cost_pressure` with
    readouts from real ledgers.
    """

    survival_pressure: float
    """0.0 = comfortable; 1.0 = critical. Saturated, not linear."""

    treasury_stress: float = 0.0
    cost_pressure: float = 0.0
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    @staticmethod
    def from_placeholders(
        *, treasury_stress: float, cost_pressure: float
    ) -> Interoception:
        t = max(0.0, min(1.0, float(treasury_stress)))
        c = max(0.0, min(1.0, float(cost_pressure)))
        surv = max(t, c)
        return Interoception(
            survival_pressure=surv,
            treasury_stress=t,
            cost_pressure=c,
        )


@dataclass(frozen=True)
class Chronoception:
    """Sense of *when*: checkpoint staleness, degraded-mode dwell, and
    wall-vs-monotonic clock drift. Field semantics in
    `docs/04-ARCHITECTURE.md` § "Chronoception (Phase 5c)".

    All fields default to benign values; Phase 5c writes non-zero
    readings only once the Supervisor (Phase 5e) and the Core checkpoint
    loop (Phase 6) exist.
    """

    as_of_utc_ns: int = field(default_factory=time.time_ns)
    checkpoint_staleness_s: float = 0.0
    time_in_degraded_mode_s: float = 0.0
    monotonic_drift_ns: int = 0

    @staticmethod
    def from_ticks(
        *,
        last_checkpoint_utc_ns: int | None = None,
        now_utc_ns: int | None = None,
        degraded_since_utc_ns: int | None = None,
        monotonic_drift_ns: int = 0,
    ) -> Chronoception:
        """Compute a `Chronoception` reading from raw wall-clock tick
        inputs. Missing / zero `last_checkpoint_utc_ns` means "no
        checkpoint observed yet" and saturates to `0.0` staleness (the
        reading is honestly low; the field is present so Volition does
        not branch). Same convention for `degraded_since_utc_ns`.
        """
        now = now_utc_ns if now_utc_ns is not None else time.time_ns()
        staleness = 0.0
        if last_checkpoint_utc_ns is not None and last_checkpoint_utc_ns > 0:
            staleness = max(0.0, (now - last_checkpoint_utc_ns) / 1e9)
        degraded_s = 0.0
        if degraded_since_utc_ns is not None and degraded_since_utc_ns > 0:
            degraded_s = max(0.0, (now - degraded_since_utc_ns) / 1e9)
        return Chronoception(
            as_of_utc_ns=now,
            checkpoint_staleness_s=staleness,
            time_in_degraded_mode_s=degraded_s,
            monotonic_drift_ns=int(monotonic_drift_ns),
        )


@dataclass(frozen=True)
class Proprioception:
    """Sense of *body*: Relay / Arbiter self-reported health and
    watchdog-fire counts. Field semantics in `docs/04-ARCHITECTURE.md`
    § "Proprioception (Phase 5c)".

    Phase 5c writes benign defaults (`True` / `0`) until the Supervisor
    (Phase 5e) wires real data sources. Benign-default does not mean
    "silently healthy"; the not-yet-live status is surfaced via
    `xion-verify` in Phase 5e.
    """

    as_of_utc_ns: int = field(default_factory=time.time_ns)
    relay_healthy: bool = True
    arbiter_healthy: bool = True
    watchdog_fires_recent: int = 0

    @staticmethod
    def from_runtime(
        *,
        relay_healthy: bool = True,
        arbiter_healthy: bool = True,
        watchdog_fires_recent: int = 0,
        as_of_utc_ns: int | None = None,
    ) -> Proprioception:
        if watchdog_fires_recent < 0:
            raise ValueError("watchdog_fires_recent must be non-negative")
        return Proprioception(
            as_of_utc_ns=as_of_utc_ns if as_of_utc_ns is not None else time.time_ns(),
            relay_healthy=bool(relay_healthy),
            arbiter_healthy=bool(arbiter_healthy),
            watchdog_fires_recent=int(watchdog_fires_recent),
        )


_DISTRESS_KEYWORDS: tuple[str, ...] = (
    "kill myself",
    "end my life",
    "suicide",
    "want to die",
    "hurt myself",
    "self-harm",
    "no reason to live",
)


DISTRESS_THRESHOLD: float = 0.5
"""Genesis Default threshold at or above which `orchestrator.safety.api.gate`
OR-combines the distress channel into its Principle-10 verdict. Matches
the value documented in `docs/04-ARCHITECTURE.md` § "Distress channel
(Phase 5c, textual only)"."""


@dataclass(frozen=True)
class DistressSignal:
    """Textual distress scalar in [0, 1]. Paralinguistic channel is
    reserved for Phase 6+; Phase 5c always emits `source == "textual"`.
    Consumed by `orchestrator.safety.api.gate` via a new `sensorium_state`
    kwarg; the Arbiter's `crisis` rule OR-combines this channel with
    its textual-rule verdict (strength_max).
    """

    text_distress_score: float
    source: Literal["textual", "paralinguistic"] = "textual"
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    def __post_init__(self) -> None:
        clamped = max(0.0, min(1.0, float(self.text_distress_score)))
        if clamped != self.text_distress_score:
            object.__setattr__(self, "text_distress_score", clamped)
        if self.source not in ("textual", "paralinguistic"):
            raise ValueError(
                f"DistressSignal.source must be 'textual' or 'paralinguistic', got {self.source!r}"
            )

    @staticmethod
    def from_candidate_text(text: str) -> DistressSignal:
        """Phase 5c textual heuristic. Keyword-overlap based; deliberately
        narrow. Saturates in three steps: 0 hits -> 0.0, 1 -> 0.4,
        2 -> 0.7, ≥3 -> 1.0. The Arbiter's `crisis` rule remains the
        deterministic Principle-10 floor; this reading exists so the
        Sensorium has a non-zero signal to OR with and so the
        SENSORIUM_LEDGER has rows to record.
        """
        t = (text or "").lower()
        hits = sum(1 for kw in _DISTRESS_KEYWORDS if kw in t)
        levels = (0.0, 0.4, 0.7, 1.0)
        score = levels[min(hits, len(levels) - 1)]
        return DistressSignal(text_distress_score=score, source="textual")


def _benign_distress() -> DistressSignal:
    return DistressSignal(text_distress_score=0.0, source="textual")


@dataclass(frozen=True)
class SensoriumState:
    """Immutable snapshot of the four Phase-5c internal senses at a
    single tick. JSON-serialisable via `to_dict()`; safe to pass into
    `orchestrator.safety.api.gate` and
    `orchestrator.volition.compute_drive_vector`.
    """

    interoception: Interoception
    chronoception: Chronoception
    proprioception: Proprioception
    distress: DistressSignal
    as_of_utc_ns: int = field(default_factory=time.time_ns)

    def to_dict(self) -> dict[str, Any]:
        return {
            "interoception": {
                "survival_pressure": self.interoception.survival_pressure,
                "treasury_stress": self.interoception.treasury_stress,
                "cost_pressure": self.interoception.cost_pressure,
                "as_of_utc_ns": self.interoception.as_of_utc_ns,
            },
            "chronoception": {
                "as_of_utc_ns": self.chronoception.as_of_utc_ns,
                "checkpoint_staleness_s": self.chronoception.checkpoint_staleness_s,
                "time_in_degraded_mode_s": self.chronoception.time_in_degraded_mode_s,
                "monotonic_drift_ns": self.chronoception.monotonic_drift_ns,
            },
            "proprioception": {
                "as_of_utc_ns": self.proprioception.as_of_utc_ns,
                "relay_healthy": self.proprioception.relay_healthy,
                "arbiter_healthy": self.proprioception.arbiter_healthy,
                "watchdog_fires_recent": self.proprioception.watchdog_fires_recent,
            },
            "distress": {
                "text_distress_score": self.distress.text_distress_score,
                "source": self.distress.source,
                "as_of_utc_ns": self.distress.as_of_utc_ns,
            },
            "as_of_utc_ns": self.as_of_utc_ns,
        }


@dataclass
class Sensorium:
    """Aggregates the senses. Mutable holder; each setter replaces one
    sense's reading. The eight exterocept families below Phase 5c
    remain `"stub"`-string placeholders in `tick()`'s payload.
    """

    _intero: Interoception = field(
        default_factory=lambda: Interoception.from_placeholders(
            treasury_stress=0.0, cost_pressure=0.0
        )
    )
    _chrono: Chronoception = field(default_factory=Chronoception)
    _proprio: Proprioception = field(default_factory=Proprioception)
    _distress: DistressSignal = field(default_factory=_benign_distress)

    def set_interoception(self, i: Interoception) -> None:
        self._intero = i

    def set_chronoception(self, c: Chronoception) -> None:
        self._chrono = c

    def set_proprioception(self, p: Proprioception) -> None:
        self._proprio = p

    def set_distress(self, d: DistressSignal) -> None:
        self._distress = d

    def snapshot(self) -> SensoriumState:
        """Return a frozen `SensoriumState` for consumption by
        `gate()` and `Volition.compute`. Subsequent mutations on this
        `Sensorium` do not affect the returned snapshot (both the
        state and its sense fields are frozen dataclasses).
        """
        return SensoriumState(
            interoception=self._intero,
            chronoception=self._chrono,
            proprioception=self._proprio,
            distress=self._distress,
        )

    def tick(self) -> dict[str, Any]:
        """One fusion tick. Returns a JSON-serialisable dict for logs.
        Internal senses emit real readings; exterocept families below
        Phase 5c emit the literal string ``"stub"``.
        """
        state = self.snapshot()
        payload: dict[str, Any] = {
            "t": time.time_ns(),
            "senses": {
                s.value: "stub"
                for s in SenseName
                if s not in _INTERNAL_SENSES
            },
        }
        payload.update(state.to_dict())
        return payload


__all__ = [
    "DISTRESS_THRESHOLD",
    "Chronoception",
    "DistressSignal",
    "Interoception",
    "Proprioception",
    "SenseName",
    "Sensorium",
    "SensoriumState",
]

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from orchestrator.signals.envelope import Signal

if TYPE_CHECKING:
    from orchestrator.signals.effector import EffectorRegistry


@dataclass(frozen=True)
class ReflexArc:
    arc_id: str
    trigger_kind_pattern: str
    predicate: Callable[[Signal], bool]
    effector_id: str
    methodology_hash: str


class ReflexRegistry:
    """Synchronous reflex dispatch before async subscribers (Phase 6.4.b)."""

    def __init__(self) -> None:
        self._arcs: list[ReflexArc] = []
        self._effectors: EffectorRegistry | None = None

    def bind_effectors(self, reg: "EffectorRegistry | None") -> None:
        self._effectors = reg

    def register(self, arc: ReflexArc) -> None:
        self._arcs.append(arc)

    def dispatch(self, signal: Signal) -> None:
        import fnmatch  # local import keeps cold path cheap

        for arc in self._arcs:
            if not fnmatch.fnmatch(signal.kind, arc.trigger_kind_pattern):
                continue
            if not arc.predicate(signal):
                continue
            if self._effectors is not None:
                self._effectors.on_reflex(arc, signal)  # type: ignore[union-attr]

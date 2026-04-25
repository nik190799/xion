"""Read models that project ``SignalBus`` state into API-friendly dicts (Phase 6.4.b)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.sensorium import SensoriumState
    from orchestrator.signals.bus import SignalBus

_OPEN_KW_RE = re.compile(r"^###\s+KW-([A-Z0-9-]+)")
_REPO_ROOT = Path(__file__).resolve().parents[2]


def _open_kw_count() -> int:
    kwp = _REPO_ROOT / "KNOWN_WEAKNESSES.md"
    try:
        t = kwp.read_text(encoding="utf-8")
    except OSError:
        return 0
    c = 0
    in_open = False
    for line in t.splitlines():
        if line.strip() == "## Open":
            in_open = True
            continue
        if in_open and line.startswith("## ") and "Open" not in line:
            break
        if in_open and _OPEN_KW_RE.match(line):
            c += 1
    return c


def _pending_phases() -> list[str]:
    return ["6.5 — Voice", "6.6 — full vital seal"]


class SensoriumView:
    @staticmethod
    def from_bus(bus: "SignalBus") -> dict[str, Any]:
        d: dict[str, Any] = {}
        for k in (
            "interoception.cost_pressure",
            "interoception.survival_pressure",
            "interoception.treasury_stress",
        ):
            s = bus.latest(k)
            if s is not None:
                p = k.split(".", 1)[1]
                d.setdefault("interoception", {})[p] = s.value
        for k in (
            "chronoception.monotonic_drift_ns",
            "chronoception.checkpoint_staleness_s",
            "chronoception.time_in_degraded_mode_s",
        ):
            s = bus.latest(k)
            if s is not None:
                p = k.split(".", 1)[1]
                d.setdefault("chronoception", {})[p] = s.value
        for k in (
            "proprioception.relay_health",
            "proprioception.arbiter_health",
            "proprioception.watchdog_fires",
        ):
            s = bus.latest(k)
            if s is not None:
                p = k.split(".", 1)[1]
                d.setdefault("proprioception", {})[p] = s.value
        s = bus.latest("distress.text_distress")
        if s is not None:
            d["distress"] = {"text_distress_score": s.value}
        return d

    @staticmethod
    def to_dict_from_bus(bus: "SignalBus") -> dict[str, Any]:
        return SensoriumView.from_bus(bus)


class TopographyView:
    @staticmethod
    def from_bus(bus: "SignalBus") -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k in bus.latest_all():
            if k.startswith("topography.") or k.startswith("inference."):
                short = k.split(".", 1)[1]
                s = bus.latest(k)
                if s is not None:
                    out[short] = s.value
        return out


class VitalsView:
    @staticmethod
    def from_bus(
        bus: "SignalBus",
        *,
        state: "SensoriumState | None" = None,
    ) -> dict[str, Any]:
        from orchestrator.vitals import get_composite_vitals

        return {
            "domains": [x.__dict__ for x in get_composite_vitals(bus=bus, state=state)],
        }


class GovernanceView:
    @staticmethod
    def from_bus(bus: "SignalBus") -> dict[str, Any]:  # noqa: ARG004
        return {
            "open_kw_count": _open_kw_count(),
            "pending_phases": _pending_phases(),
        }

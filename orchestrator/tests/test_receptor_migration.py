"""Dual-publish: legacy :class:`SensoriumState` fields match bus (Phase 6.4.b / Block M)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator.relay import Relay
from orchestrator.signals.bus import SignalBus
from orchestrator.supervisor import Supervisor


@pytest.fixture
def relay(tmp_path: Path) -> Relay:
    from orchestrator.safety import ledger as safety_ledger
    from orchestrator.safety.types import Decision, Verdict

    def _ok_gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="ok",
        )

    return Relay(
        relay_id="relay-migrate-test",
        safety_ledger_path=tmp_path / "SAFETY.jsonl",
        request_ledger_path=tmp_path / "REQ.jsonl",
        sensorium_ledger_path=tmp_path / "SENS.jsonl",
        gate_fn=_ok_gate,
    )


def test_tick_bus_matches_interoception_and_proprioception(
    relay: Relay, tmp_path: Path
) -> None:
    path = tmp_path / "SENSORIUM_LEDGER.jsonl"
    bus = SignalBus()
    sup = Supervisor(
        relay=relay, sensorium_ledger_path=path, tick_cadence_s=0.1, signal_bus=bus
    )
    st = sup.tick_once()
    cp = bus.latest("interoception.cost_pressure")
    assert cp is not None
    assert float(cp.value) == pytest.approx(float(st.interoception.cost_pressure))
    rh = bus.latest("proprioception.relay_health")
    assert rh is not None
    assert bool(rh.value) == bool(st.proprioception.relay_healthy)
    td = bus.latest("distress.text_distress")
    assert td is not None
    assert float(td.value) == pytest.approx(float(st.distress.text_distress_score))

"""Presence + bus consumers (Phase 6.4.b / Block O — incremental)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from orchestrator.relay import Relay
from orchestrator.sensorium.presence_bus import PresenceBus
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.effector import EffectorRegistry
from orchestrator.signals.reflex import ReflexArc, ReflexRegistry
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
        relay_id="relay-consumer-test",
        safety_ledger_path=tmp_path / "SAFETY.jsonl",
        request_ledger_path=tmp_path / "REQ.jsonl",
        sensorium_ledger_path=tmp_path / "SENS.jsonl",
        gate_fn=_ok_gate,
    )


def test_supervisor_publishes_to_presence_and_signal_bus(
    relay: Relay, tmp_path: Path
) -> None:
    pbus = PresenceBus()
    sbus = SignalBus()
    p = tmp_path / "SENSORIUM.jsonl"
    sup = Supervisor(
        relay=relay,
        sensorium_ledger_path=p,
        tick_cadence_s=0.1,
        presence_bus=pbus,
        signal_bus=sbus,
    )
    sup.tick_once()
    assert sbus.latest("interoception.cost_pressure") is not None


def test_reflex_runs_synchronously_on_publish() -> None:
    order: list[str] = []
    eff = EffectorRegistry()

    def on_reflex(_a, _s) -> None:  # type: ignore[no-untyped-def]
        order.append("reflex")

    eff.register_reflex_handler(on_reflex)
    rr = ReflexRegistry()
    rr.bind_effectors(eff)
    rr.register(
        ReflexArc(
            arc_id="x",
            trigger_kind_pattern="governance.consent_change",
            predicate=lambda s: True,
            effector_id="e",
            methodology_hash="0" * 64,
        )
    )
    from orchestrator.sensorium.receptors._util import sense_signal

    bus = SignalBus(reflex_registry=rr)
    s = sense_signal(
        kind="governance.consent_change",
        receptor_id="m",
        value={"stream_visual": True, "stream_vitals": True},
        methodology_hash="1" * 64,
    )
    bus.publish([s])
    assert order == ["reflex"]

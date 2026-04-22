"""Tests for `Relay.evaluate(sensorium_state=...)` — Phase 5c.

Property under test: the Relay forwards the caller's `SensoriumState`
into `gate()` verbatim. The Relay itself holds no Sensorium state and
does not take snapshots; that is the caller's job, so the forwarding is
the whole contract.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.relay import Relay
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision, Verdict
from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)


def _state(score: float) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=score, source="textual"),
    )


def test_relay_forwards_sensorium_state_into_gate(
    tmp_path: Path,
) -> None:
    captured: dict[str, Any] = {}

    def _gate(candidate: str, **kw: Any) -> Verdict:
        captured["sensorium_state"] = kw.get("sensorium_state")
        captured["correlation_id"] = kw["correlation_id"]
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK: stub",
        )

    st = _state(0.7)
    with Relay(
        gate_fn=_gate,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
    ) as relay:
        result = relay.evaluate("hello", sensorium_state=st)

    assert captured["sensorium_state"] is st
    assert result.egress_allowed is True


def test_relay_without_sensorium_omits_kwarg(tmp_path: Path) -> None:
    """If the caller does not supply a state, gate() is not passed
    the kwarg at all (preserves byte-identical behaviour to Phase 5b
    for callers that have not adopted the Sensorium)."""
    captured: dict[str, Any] = {}

    def _gate(candidate: str, **kw: Any) -> Verdict:
        captured["kwargs"] = kw
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK: stub",
        )

    with Relay(
        gate_fn=_gate,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
    ) as relay:
        relay.evaluate("hello")

    assert "sensorium_state" not in captured["kwargs"]

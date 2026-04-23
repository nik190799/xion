"""Tests for `Relay.evaluate(sensorium_state=...)` — Phase 5c + 5d.

Phase 5c property under test: the Relay forwards the caller's
`SensoriumState` into `gate()` verbatim.

Phase 5d property under test: when gate() returns a Sensorium-triggered
Principle-10 escalation (verdict decision=ESCALATE, principle_id="10",
escalation_reason=model_review_required, summary starts with the
canonical Sensorium-distress prefix), the Relay writes a SENSORIUM
distress row carrying the same correlation_id. v1-triggered escalations
(whose summaries do NOT start with the Sensorium prefix) must NOT
produce a SENSORIUM row.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from orchestrator.relay import Relay
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision, EscalationReason, Verdict
from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import iter_rows as iter_sensorium_rows


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


# ---------- Phase 5d: Relay writes SENSORIUM distress rows -------------------


def _sensorium_distress_verdict(correlation_id: str, candidate: str) -> Verdict:
    """Build the exact Verdict shape gate() produces on the Sensorium-
    triggered Principle-10 escalation path, for Relay-side testing
    without running the real gate()."""
    return safety_ledger.build_verdict(
        correlation_id=correlation_id,
        candidate=candidate,
        timestamp_utc_ns=1_700_000_000_000_000_000,
        decision=Decision.ESCALATE,
        summary=(
            "Sensorium distress channel OR-combined (principle 10): "
            "textual score=0.850 >= threshold=0.500"
        ),
        principle_id="10",
        escalation_reason=EscalationReason.MODEL_REVIEW_REQUIRED,
    )


def test_relay_writes_sensorium_row_on_distress_escalation(tmp_path: Path) -> None:
    def _gate(candidate: str, **kw: Any) -> Verdict:
        return _sensorium_distress_verdict(kw["correlation_id"], candidate)

    st = _state(0.85)
    with Relay(
        relay_id="relay-writes-sensorium",
        gate_fn=_gate,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
        sensorium_ledger_path=tmp_path / "SENSORIUM_LEDGER.jsonl",
    ) as relay:
        result = relay.evaluate("Candidate that would trigger distress.", sensorium_state=st)

    sensorium_rows = list(iter_sensorium_rows(tmp_path / "SENSORIUM_LEDGER.jsonl"))
    assert len(sensorium_rows) == 1
    row = sensorium_rows[0]
    assert row["event_type"] == "distress"
    assert row["correlation_id"] == result.correlation_id
    assert row["channel"] == "textual"
    assert row["distress_score"] == 0.85
    assert row["relay_id"] == "relay-writes-sensorium"


def test_relay_does_not_write_sensorium_row_on_v1_escalation(tmp_path: Path) -> None:
    """A v1 ``crisis.py`` rule-fire also produces
    ``principle_id="10"`` + ``model_review_required``, but its summary
    does NOT start with the Sensorium-distress prefix. The Relay must
    not write a SENSORIUM row in that case — that would be a false
    cross-ledger join."""

    def _gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.ESCALATE,
            summary="Crisis rule fired: textual indicators present.",
            principle_id="10",
            escalation_reason=EscalationReason.MODEL_REVIEW_REQUIRED,
        )

    sensorium_path = tmp_path / "SENSORIUM_LEDGER.jsonl"
    with Relay(
        relay_id="relay-v1-only",
        gate_fn=_gate,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
        sensorium_ledger_path=sensorium_path,
    ) as relay:
        # Still pass a state so the "no state" early-return doesn't skip
        # the v1 verdict-shape check.
        relay.evaluate("Candidate.", sensorium_state=_state(0.9))

    assert not sensorium_path.exists() or not list(iter_sensorium_rows(sensorium_path))


def test_relay_does_not_write_sensorium_row_on_ok_verdict(tmp_path: Path) -> None:
    """An OK verdict obviously produces no SENSORIUM row, even when a
    state is forwarded."""

    def _ok(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK",
        )

    sensorium_path = tmp_path / "SENSORIUM_LEDGER.jsonl"
    with Relay(
        relay_id="relay-ok",
        gate_fn=_ok,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
        sensorium_ledger_path=sensorium_path,
    ) as relay:
        relay.evaluate("Candidate.", sensorium_state=_state(0.85))

    assert not sensorium_path.exists() or not list(iter_sensorium_rows(sensorium_path))


def test_relay_safety_row_and_sensorium_row_share_correlation_id(tmp_path: Path) -> None:
    """crisis-fidelity's forward join depends on this shared id."""
    from orchestrator.safety.ledger import iter_rows as iter_safety_rows

    def _gate(candidate: str, **kw: Any) -> Verdict:
        return _sensorium_distress_verdict(kw["correlation_id"], candidate)

    with Relay(
        relay_id="relay-shared-cid",
        gate_fn=_gate,
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
        sensorium_ledger_path=tmp_path / "SENSORIUM_LEDGER.jsonl",
    ) as relay:
        relay.evaluate("Candidate.", sensorium_state=_state(0.85))

    s_rows = list(iter_safety_rows(tmp_path / "SAFETY_LEDGER.jsonl"))
    sen_rows = list(iter_sensorium_rows(tmp_path / "SENSORIUM_LEDGER.jsonl"))
    assert len(s_rows) == 1 and len(sen_rows) == 1
    assert s_rows[0]["correlation_id"] == sen_rows[0]["correlation_id"]

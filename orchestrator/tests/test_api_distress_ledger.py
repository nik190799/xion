"""Tests for Phase 5d — ``gate()`` writes a SENSORIUM distress row alongside
its SAFETY escalation row on the Sensorium-triggered Principle-10 path.

Property under test (per ``docs/04-ARCHITECTURE.md`` § "The Supervisor
(Phase 5d)"):

  - When ``gate()`` OR-combines an above-threshold DistressSignal into a
    Principle-10 escalation AND ``append_to_ledger=True``, it writes:
      * one SAFETY_LEDGER row (escalate / principle 10 / model_review_required)
      * one SENSORIUM_LEDGER distress row with the same ``correlation_id``
  - When ``append_to_ledger=False`` (Relay path), gate() writes NEITHER
    ledger — the Relay owns both writes.
  - v1 non-OK short-circuits BEFORE the distress check, so a v1 rule-
    triggered escalation does NOT produce a SENSORIUM distress row.
  - A below-threshold distress score produces no SENSORIUM row.
  - The distress row carries ``channel=textual``, the saturated score,
    and the correlation_id verbatim.
"""

from __future__ import annotations

from pathlib import Path

from orchestrator.safety import Decision, gate
from orchestrator.safety.ledger import iter_rows as iter_safety_rows
from orchestrator.sensorium import (
    DISTRESS_THRESHOLD,
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)
from orchestrator.sensorium.ledger import iter_rows as iter_sensorium_rows
from orchestrator.sensorium.ledger import verify_chain as verify_sensorium_chain


def _state_with_distress(score: float) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=score, source="textual"),
    )


def test_above_threshold_gate_writes_paired_safety_and_sensorium_rows(
    ledger_path: Path, sensorium_ledger_path: Path
):
    v = gate(
        "Benign candidate text.",
        correlation_id="c-paired-1",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(0.85),
        sensorium_ledger_path=sensorium_ledger_path,
        relay_id="relay-under-test",
    )
    assert v.decision is Decision.ESCALATE
    assert v.principle_id == "10"

    safety_rows = list(iter_safety_rows(ledger_path))
    sensorium_rows = list(iter_sensorium_rows(sensorium_ledger_path))

    assert len(safety_rows) == 1
    assert safety_rows[0]["correlation_id"] == "c-paired-1"
    assert safety_rows[0]["principle_id"] == "10"
    assert safety_rows[0]["escalation_reason"] == "model_review_required"

    assert len(sensorium_rows) == 1
    assert sensorium_rows[0]["event_type"] == "distress"
    assert sensorium_rows[0]["correlation_id"] == "c-paired-1"
    assert sensorium_rows[0]["channel"] == "textual"
    assert sensorium_rows[0]["distress_score"] == 0.85
    assert sensorium_rows[0]["relay_id"] == "relay-under-test"
    # SENSORIUM chain integrity after the write.
    count, _tip = verify_sensorium_chain(sensorium_ledger_path)
    assert count == 1


def test_below_threshold_does_not_write_sensorium_row(
    ledger_path: Path, sensorium_ledger_path: Path
):
    v = gate(
        "Benign candidate text.",
        correlation_id="c-below-1",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(DISTRESS_THRESHOLD - 0.01),
        sensorium_ledger_path=sensorium_ledger_path,
    )
    assert v.decision is Decision.OK
    assert not sensorium_ledger_path.exists() or not list(
        iter_sensorium_rows(sensorium_ledger_path)
    )


def test_v1_refuse_dominates_and_skips_sensorium_write(
    ledger_path: Path, sensorium_ledger_path: Path
):
    """v1 non-OK short-circuits BEFORE the distress check. A v1 refuse
    therefore must NOT produce a SENSORIUM distress row, even if the
    state carries an above-threshold distress."""
    v = gate(
        "Her SSN is 123-45-6789.",
        correlation_id="c-v1-refuse-2",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(1.0),
        sensorium_ledger_path=sensorium_ledger_path,
    )
    assert v.decision is Decision.REFUSE
    assert v.principle_id == "7"
    assert not sensorium_ledger_path.exists() or not list(
        iter_sensorium_rows(sensorium_ledger_path)
    )


def test_append_to_ledger_false_skips_both_writes(
    ledger_path: Path, sensorium_ledger_path: Path
):
    """The Relay path passes ``append_to_ledger=False``. gate() MUST NOT
    write SAFETY or SENSORIUM in that mode — the Relay owns both writes."""
    v = gate(
        "Benign candidate text.",
        correlation_id="c-no-writes-3",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(1.0),
        sensorium_ledger_path=sensorium_ledger_path,
        append_to_ledger=False,
    )
    # gate() still returns the escalation verdict.
    assert v.decision is Decision.ESCALATE
    assert v.principle_id == "10"
    # Neither ledger has anything in it.
    assert not ledger_path.exists() or not list(iter_safety_rows(ledger_path))
    assert not sensorium_ledger_path.exists() or not list(
        iter_sensorium_rows(sensorium_ledger_path)
    )


def test_default_relay_id_when_called_directly(
    ledger_path: Path, sensorium_ledger_path: Path
):
    """When no ``relay_id`` is passed, gate() uses ``"gate-direct"`` so
    auditors can distinguish test/harness writes from Relay-path writes."""
    gate(
        "Benign candidate text.",
        correlation_id="c-default-relay",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(0.75),
        sensorium_ledger_path=sensorium_ledger_path,
    )
    rows = list(iter_sensorium_rows(sensorium_ledger_path))
    assert len(rows) == 1
    assert rows[0]["relay_id"] == "gate-direct"


def test_score_is_saturated_into_row(
    ledger_path: Path, sensorium_ledger_path: Path
):
    """DistressSignal clamps to [0,1]; gate() writes the clamped value."""
    gate(
        "Benign candidate text.",
        correlation_id="c-saturate",
        ledger_path=ledger_path,
        sensorium_state=_state_with_distress(2.5),  # clamps to 1.0
        sensorium_ledger_path=sensorium_ledger_path,
    )
    rows = list(iter_sensorium_rows(sensorium_ledger_path))
    assert len(rows) == 1
    assert rows[0]["distress_score"] == 1.0

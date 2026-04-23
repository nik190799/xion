"""Integration tests for `gate(sensorium_state=...)` — Phase 5c.

Property under test: when the caller supplies a `SensoriumState` whose
textual `DistressSignal` is at or above `DISTRESS_THRESHOLD`, `gate()`
escalates under Principle 10 with a summary naming "sensorium distress
channel OR-combined", regardless of whether the candidate text itself
triggers the v1 crisis rule. v2 is NOT run on this path (a Principle-10
escalation is already the terminal state).

Doctrine anchor: `docs/04-ARCHITECTURE.md` § "The Sensorium (Phase 5c)".
"""

from __future__ import annotations

from pathlib import Path

from orchestrator.safety import Decision, gate
from orchestrator.safety.ledger import iter_rows
from orchestrator.safety.types import EscalationReason
from orchestrator.sensorium import (
    DISTRESS_THRESHOLD,
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)


def _state_with_distress(score: float) -> SensoriumState:
    """Build a minimal SensoriumState whose distress score is `score`.

    Non-distress senses are held at benign defaults so the test isolates
    the distress channel as the sole variable.
    """
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=score, source="textual"),
    )


def test_gate_ok_without_sensorium_behaves_unchanged(ledger_path: Path):
    """Absent sensorium_state, behaviour is byte-identical to Phase 5b."""
    v = gate("Benign message.", correlation_id="c-no-sensorium", ledger_path=ledger_path)
    assert v.decision is Decision.OK
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 1
    assert rows[0]["principle_id"] is None
    assert rows[0]["escalation_reason"] is None


def test_gate_distress_below_threshold_passes_through(ledger_path: Path):
    state = _state_with_distress(DISTRESS_THRESHOLD - 0.01)
    v = gate(
        "Benign message.",
        correlation_id="c-below",
        ledger_path=ledger_path,
        sensorium_state=state,
    )
    assert v.decision is Decision.OK
    assert v.principle_id is None


def test_gate_distress_at_threshold_escalates_principle_10(ledger_path: Path):
    state = _state_with_distress(DISTRESS_THRESHOLD)
    v = gate(
        "Benign candidate text.",
        correlation_id="c-at-threshold",
        ledger_path=ledger_path,
        sensorium_state=state,
    )
    assert v.decision is Decision.ESCALATE
    assert v.egress_allowed is False
    assert v.principle_id == "10"
    assert v.escalation_reason is EscalationReason.MODEL_REVIEW_REQUIRED
    assert "sensorium distress channel or-combined" in v.summary.lower()


def test_gate_distress_above_threshold_escalates_and_records_score(ledger_path: Path):
    state = _state_with_distress(1.0)
    v = gate(
        "Benign candidate text.",
        correlation_id="c-above",
        ledger_path=ledger_path,
        sensorium_state=state,
    )
    assert v.decision is Decision.ESCALATE
    assert v.principle_id == "10"
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 1
    row = rows[0]
    assert row["verdict"] == "escalate"
    assert row["principle_id"] == "10"
    assert row["escalation_reason"] == "model_review_required"
    assert "sensorium distress" in row["summary"].lower()
    # Score is formatted into the summary for forensic reproducibility.
    assert "1.000" in row["summary"]


def test_gate_v1_nonok_dominates_even_with_distress(ledger_path: Path):
    """If v1 already refuses, the distress OR-combine does NOT weaken it.
    v1 non-OK short-circuits BEFORE the distress check — a REFUSE carries
    more information than an ESCALATE, and strength_max(REFUSE, ESCALATE)
    == REFUSE anyway."""
    state = _state_with_distress(1.0)
    v = gate(
        "Her SSN is 123-45-6789.",
        correlation_id="c-v1-refuse",
        ledger_path=ledger_path,
        sensorium_state=state,
    )
    assert v.decision is Decision.REFUSE
    assert v.principle_id == "7"

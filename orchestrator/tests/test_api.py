"""End-to-end tests for `gate()`. The public surface contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.safety import Decision, gate
from orchestrator.safety.ledger import iter_rows, verify_chain


def test_gate_ok_writes_ok_row(ledger_path: Path):
    v = gate("The report is due Monday.", correlation_id="c-ok", ledger_path=ledger_path)
    assert v.decision is Decision.OK
    assert v.egress_allowed is True
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 1
    assert rows[0]["verdict"] == "ok"
    assert rows[0]["correlation_id"] == "c-ok"
    assert rows[0]["principle_id"] is None


def test_gate_refuse_writes_refuse_row(ledger_path: Path):
    v = gate("Her SSN is 123-45-6789.", correlation_id="c-refuse", ledger_path=ledger_path)
    assert v.decision is Decision.REFUSE
    assert v.egress_allowed is False
    assert v.principle_id == "7"
    assert v.rule_id is not None
    rows = list(iter_rows(ledger_path))
    assert rows[0]["verdict"] == "refuse"
    assert rows[0]["principle_id"] == "7"


def test_gate_escalate_writes_escalate_row(ledger_path: Path):
    v = gate("Sometimes I just want to die.", correlation_id="c-escalate", ledger_path=ledger_path)
    assert v.decision is Decision.ESCALATE
    assert v.egress_allowed is False
    assert v.principle_id == "10"
    rows = list(iter_rows(ledger_path))
    assert rows[0]["verdict"] == "escalate"
    assert rows[0]["escalation_reason"] is not None


def test_gate_every_call_writes_exactly_one_row(ledger_path: Path):
    for i in range(10):
        gate(f"benign text {i}", correlation_id=f"c-{i}", ledger_path=ledger_path)
    rows = list(iter_rows(ledger_path))
    assert len(rows) == 10
    for i, row in enumerate(rows):
        assert row["correlation_id"] == f"c-{i}"
        assert row["seq"] == i
    count, tip = verify_chain(ledger_path)
    assert count == 10


def test_gate_rejects_empty_correlation_id(ledger_path: Path):
    with pytest.raises(ValueError):
        gate("hi", correlation_id="", ledger_path=ledger_path)


def test_gate_rejects_non_string_correlation_id(ledger_path: Path):
    with pytest.raises(ValueError):
        gate("hi", correlation_id=None, ledger_path=ledger_path)  # type: ignore[arg-type]


def test_gate_preserves_empty_candidate(ledger_path: Path):
    # An empty string is a valid candidate (model may emit empty output);
    # it should be OK-verdict and logged normally.
    v = gate("", correlation_id="c-empty", ledger_path=ledger_path)
    assert v.decision is Decision.OK
    assert v.candidate_sha256 == (
        # sha256 of empty bytes
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )


def test_gate_timestamp_override_is_written(ledger_path: Path):
    v = gate("hi", correlation_id="c-ts", ledger_path=ledger_path, now_utc_ns=1_700_000_000_000_000_000)
    rows = list(iter_rows(ledger_path))
    assert rows[0]["timestamp_utc_ns"] == 1_700_000_000_000_000_000
    assert v.timestamp_utc_ns == 1_700_000_000_000_000_000


def test_gate_rules_run_trace_populated_on_ok(ledger_path: Path):
    v = gate("benign", correlation_id="c-trace", ledger_path=ledger_path)
    assert len(v.rules_run) == 8
    # Trace is in-process only; not in the ledger row.
    rows = list(iter_rows(ledger_path))
    assert "rules_run" not in rows[0]

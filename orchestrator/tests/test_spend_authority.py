from __future__ import annotations

import json

import pytest
from xion_verify.commands.spend_posture import check_spend_posture

from orchestrator.spend_arbitration import SpendProposal, arbitrate_contested_headroom
from orchestrator.spend_authority.ledger import SpendAuthorityRecord, append, verify_chain


def _record(**overrides) -> SpendAuthorityRecord:
    values = {
        "decision_id": "d1",
        "spend_class": "routine_ops",
        "active_posture": "S2_operator_strategic",
        "active_mode": "baseline",
        "approver_class": "ao_core",
        "authority_decision": "approved",
        "evidence_bundle_hash": "a" * 64,
        "inflow_tag_reference": "",
        "fund_source": "Operating Float",
        "runway_measurements": {"runway_weeks": 12.0},
        "proposed_amount": 10.0,
    }
    values.update(overrides)
    return SpendAuthorityRecord(**values)


def test_spend_authority_ledger_hash_chain(tmp_path) -> None:
    ledger = tmp_path / "SPEND_AUTHORITY_LEDGER.jsonl"

    append(ledger, _record())
    append(ledger, _record(decision_id="d2", spend_class="one_time_acceleration", approver_class="operator"))

    assert verify_chain(ledger) == []


def test_spend_authority_ledger_detects_tamper(tmp_path) -> None:
    ledger = tmp_path / "SPEND_AUTHORITY_LEDGER.jsonl"
    append(ledger, _record())
    row = json.loads(ledger.read_text(encoding="utf-8"))
    row["proposed_amount"] = 99.0
    ledger.write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    assert any("this_hash mismatch" in error for error in verify_chain(ledger))


def test_spend_posture_rejects_wrong_authority(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl", _record(approver_class="operator"))

    errors = check_spend_posture(tmp_path)

    assert any("not allowed" in error for error in errors)


def test_spend_posture_rejects_inflow_advanced_posture(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(
        ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl",
        _record(
            spend_class="posture_transition",
            active_posture="S1_operator_all",
            approver_class="operator",
            inflow_tag_reference="grant:123",
        ),
    )

    errors = check_spend_posture(tmp_path)

    assert any("inflow tag" in error for error in errors)


def test_spend_arbitration_prefers_drive_then_tiebreakers() -> None:
    winner = arbitrate_contested_headroom(
        [
            SpendProposal(2, "meaning-fast", "meaning", 0, 0, 10, 0.1),
            SpendProposal(1, "survival-later", "survival", 5, 5, 0, 0.9),
        ]
    )

    assert winner.proposal_id == "survival-later"


def test_spend_arbitration_requires_proposals() -> None:
    with pytest.raises(ValueError):
        arbitrate_contested_headroom([])

from __future__ import annotations

from orchestrator.spend_authority.ledger import SpendAuthorityRecord
from orchestrator.spend_authority.writer import append_to_repo_ledger, default_ledger_path


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


def test_append_to_repo_ledger_writes_under_ledgers(tmp_path) -> None:
    ledger = default_ledger_path(tmp_path)
    row = append_to_repo_ledger(tmp_path, _record())
    assert ledger.is_file()
    body = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(body) == 1
    assert row["decision_id"] == "d1"


def test_append_to_repo_ledger_custom_path(tmp_path) -> None:
    alt = tmp_path / "custom.jsonl"
    append_to_repo_ledger(tmp_path, _record(), ledger_path=alt)
    assert alt.is_file()

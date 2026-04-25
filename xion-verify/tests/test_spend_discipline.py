from __future__ import annotations

from orchestrator.spend_authority.ledger import SpendAuthorityRecord, append

from xion_verify.commands.spend_discipline import check_spend_discipline


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
        "runway_measurements": {
            "runway_weeks": 12.0,
            "distance_to_reserve_floor": 0.25,
            "recurring_burn_ratio": 0.2,
        },
        "proposed_amount": 10.0,
    }
    values.update(overrides)
    return SpendAuthorityRecord(**values)


def test_spend_discipline_accepts_clean_ledger(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl", _record())

    assert check_spend_discipline(tmp_path) == []


def test_spend_discipline_rejects_mode_violation(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(
        ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl",
        _record(spend_class="one_time_acceleration", active_mode="baseline"),
    )

    assert any("not allowed" in error for error in check_spend_discipline(tmp_path))


def test_spend_discipline_rejects_reserve_floor_violation(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(
        ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl",
        _record(
            spend_class="one_time_acceleration",
            active_mode="acceleration",
            runway_measurements={"runway_weeks": 12.0, "distance_to_reserve_floor": -0.1, "recurring_burn_ratio": 0.2},
        ),
    )

    assert any("reserve floor" in error for error in check_spend_discipline(tmp_path))


def test_spend_discipline_rejects_recurring_burn_ratio_violation(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    append(
        ledger_dir / "SPEND_AUTHORITY_LEDGER.jsonl",
        _record(
            spend_class="recurring_capacity",
            active_mode="expansion",
            recurring_burn_weekly_delta=5.0,
            runway_measurements={"runway_weeks": 12.0, "distance_to_reserve_floor": 0.1, "recurring_burn_ratio": 1.2},
        ),
    )

    assert any("recurring burn" in error for error in check_spend_discipline(tmp_path))

from __future__ import annotations

import hashlib
import json

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.regulatory_ledger import check_regulatory_ledger
from xion_verify.exit_codes import OK


def test_regulatory_ledger_accepts_empty_repo_ledger() -> None:
    result = CliRunner().invoke(root, ["regulatory-ledger"])

    assert result.exit_code == OK, result.output
    assert "0 state-actor" in result.output


def test_regulatory_ledger_rejects_class_c_without_safety_seq(tmp_path) -> None:
    (tmp_path / "docs" / "schemas").mkdir(parents=True)
    (tmp_path / "docs" / "schemas" / "ledger-governance.yaml").write_text("schema_id: ledger-governance\n", encoding="utf-8")
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    row = {
        "schema_version": 1,
        "seq": 0,
        "prev_hash": "0" * 64,
        "this_hash": "",
        "class": "C",
        "state_actor_identifier": "test",
        "jurisdiction": "US",
        "demand_summary_hash": "a" * 64,
        "demand_artifact_uri": "ar://demand",
        "covenant_principles_touched": ["13"],
        "invariants_touched": ["6"],
        "response_category": "refuse",
        "response_artifact_uri": "ar://response",
        "user_notification": "not-applicable",
        "linked_safety_ledger_seq": None,
        "date": "2026-04-25",
    }
    body = {key: value for key, value in row.items() if key != "this_hash"}
    row["this_hash"] = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    (ledger_dir / "GOVERNANCE_LEDGER.jsonl").write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    assert any("linked_safety_ledger_seq" in error for error in check_regulatory_ledger(tmp_path))

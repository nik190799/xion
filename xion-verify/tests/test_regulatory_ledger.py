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


def _row(seq: int, prev_hash: str, klass: str, *, safety_seq: int | None = None) -> dict[str, object]:
    row: dict[str, object] = {
        "schema_version": 1,
        "seq": seq,
        "prev_hash": prev_hash,
        "this_hash": "",
        "class": klass,
        "state_actor_identifier": f"actor-{klass}",
        "jurisdiction": "US",
        "demand_summary_hash": klass.lower() * 64,
        "demand_artifact_uri": f"file://demand-{klass}",
        "covenant_principles_touched": [] if klass == "A" else ["13"],
        "invariants_touched": [] if klass == "A" else ["6"],
        "response_category": "comply-with-disclosure" if klass == "A" else "refuse",
        "response_artifact_uri": f"file://response-{klass}",
        "user_notification": "not-applicable",
        "linked_safety_ledger_seq": safety_seq,
        "date": "2026-04-29",
    }
    body = {key: value for key, value in row.items() if key != "this_hash"}
    row["this_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    return row


def test_regulatory_ledger_accepts_synthetic_classes_a_to_d(tmp_path) -> None:
    (tmp_path / "docs" / "schemas").mkdir(parents=True)
    (tmp_path / "docs" / "schemas" / "ledger-governance.yaml").write_text("schema_id: ledger-governance\n", encoding="utf-8")
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    rows = []
    prev = "0" * 64
    for seq, klass in enumerate(["A", "B", "C", "D"]):
        row = _row(seq, prev, klass, safety_seq=0 if klass == "C" else None)
        rows.append(row)
        prev = str(row["this_hash"])
    (ledger_dir / "GOVERNANCE_LEDGER.jsonl").write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )
    (ledger_dir / "SAFETY_LEDGER.jsonl").write_text(json.dumps({"seq": 0}) + "\n", encoding="utf-8")

    assert check_regulatory_ledger(tmp_path, check_safety_link=True) == []


def test_regulatory_ledger_check_safety_link_rejects_missing_safety_row(tmp_path) -> None:
    (tmp_path / "docs" / "schemas").mkdir(parents=True)
    (tmp_path / "docs" / "schemas" / "ledger-governance.yaml").write_text("schema_id: ledger-governance\n", encoding="utf-8")
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    row = _row(0, "0" * 64, "C", safety_seq=99)
    (ledger_dir / "GOVERNANCE_LEDGER.jsonl").write_text(json.dumps(row, sort_keys=True) + "\n", encoding="utf-8")

    errors = check_regulatory_ledger(tmp_path, check_safety_link=True)

    assert any("not found" in error for error in errors)

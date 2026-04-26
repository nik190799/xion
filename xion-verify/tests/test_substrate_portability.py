from __future__ import annotations

import hashlib
import json

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.substrate_portability import (
    check_substrate_portability,
    evaluate_substrate_portability,
)
from xion_verify.exit_codes import NOT_YET_SEALED, OK


def test_substrate_portability_command_keeps_placeholder_repo_ledger_unsealed() -> None:
    result = CliRunner().invoke(root, ["substrate-portability"])

    assert result.exit_code == NOT_YET_SEALED, result.output
    assert "non-laptop secondary" in result.output


def test_substrate_portability_accepts_non_laptop_secondary(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    row = {
        "schema_version": 1,
        "seq": 0,
        "prev_hash": "0" * 64,
        "this_hash": "",
        "as_of_utc_ns": 1,
        "secondary_substrate_id": "akash-testnet-standby",
        "primary_tip": "a",
        "secondary_tip": "a",
        "replayed_rows": 1000,
        "tip_parity": True,
    }
    body = {key: value for key, value in row.items() if key != "this_hash"}
    row["this_hash"] = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()
    (ledger_dir / "SUBSTRATE_DRYRUN_LEDGER.jsonl").write_text(
        json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    code, messages = evaluate_substrate_portability(tmp_path)

    assert code == OK
    assert messages == []


def test_substrate_portability_rejects_tip_mismatch(tmp_path) -> None:
    ledger_dir = tmp_path / "ledgers"
    ledger_dir.mkdir()
    (ledger_dir / "SUBSTRATE_DRYRUN_LEDGER.jsonl").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "seq": 0,
                "prev_hash": "0" * 64,
                "this_hash": "bad",
                "as_of_utc_ns": 0,
                "secondary_substrate_id": "secondary",
                "primary_tip": "a",
                "secondary_tip": "b",
                "replayed_rows": 1000,
                "tip_parity": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert any("tip_parity" in error for error in check_substrate_portability(tmp_path))

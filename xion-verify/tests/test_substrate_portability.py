from __future__ import annotations

import json

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.substrate_portability import check_substrate_portability
from xion_verify.exit_codes import OK


def test_substrate_portability_command_accepts_repo_ledger() -> None:
    result = CliRunner().invoke(root, ["substrate-portability"])

    assert result.exit_code == OK, result.output
    assert "tip parity" in result.output


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

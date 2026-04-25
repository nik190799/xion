from __future__ import annotations

import json

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.treasury import check_treasury
from xion_verify.exit_codes import OK


def test_treasury_command_accepts_repo_manifest() -> None:
    result = CliRunner().invoke(root, ["treasury"])

    assert result.exit_code == OK, result.output
    assert "deployment residual" in result.output


def test_treasury_rejects_bad_bridge_cap(tmp_path) -> None:
    (tmp_path / "contracts" / "treasury").mkdir(parents=True)
    (tmp_path / "contracts" / "treasury" / "MasterTreasury.sol").write_text("//", encoding="utf-8")
    (tmp_path / "contracts" / "treasury" / "Vault.sol").write_text("//", encoding="utf-8")
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "TREASURY_VAULTS.json").write_text(
        json.dumps({"schema_version": 1, "bridge_exposure_cap_bps": 10001, "vaults": []}),
        encoding="utf-8",
    )

    assert any("bridge_exposure_cap_bps" in error for error in check_treasury(tmp_path))

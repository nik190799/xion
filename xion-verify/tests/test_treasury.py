from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from xion_verify.cli import root
from xion_verify.commands.treasury import check_treasury
from xion_verify.exit_codes import OK


def test_treasury_command_accepts_repo_manifest() -> None:
    result = CliRunner().invoke(root, ["treasury"])

    assert result.exit_code == OK, result.output
    assert "deployment residual" in result.output


def _minimal_treasury_sol_files(repo: Path) -> None:
    (repo / "contracts" / "treasury").mkdir(parents=True)
    (repo / "contracts" / "treasury" / "MasterTreasury.sol").write_text(
        "// function aggregateTotals\n// function requestReplenish\n// event ReplenishRequested\n",
        encoding="utf-8",
    )
    (repo / "contracts" / "treasury" / "Vault.sol").write_text(
        "// SafeERC20 IERC20 SafeERC20 function balanceOf function withdraw "
        "// receive() external payable\n",
        encoding="utf-8",
    )


def test_treasury_rejects_audit_without_correction_record(tmp_path) -> None:
    _minimal_treasury_sol_files(tmp_path)
    (tmp_path / "genesis").mkdir()
    tier1 = [
        {"asset": "AR", "purpose": "ar"},
        {"asset": "USDC", "purpose": "usd"},
        {"asset": "ETH", "purpose": "eth"},
        {"asset": "TAO", "purpose": "tao"},
    ]
    manifest = {
        "schema_version": 1,
        "bridge_exposure_cap_bps": 1000,
        "vaults": [],
        "tier1_operating_tokens": tier1,
        "treasury_audit_arweave_tx": "wfZMZaLLLVwsb0PodZ0aeQqs2x158j1vI00b67_6Csg",
        "treasury_audit_correction_arweave_tx": "",
    }
    (tmp_path / "genesis" / "TREASURY_VAULTS.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    assert any("treasury_audit_correction" in error for error in check_treasury(tmp_path))


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

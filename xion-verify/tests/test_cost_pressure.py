from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_cost_pressure_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    # Pre-create the ledger so we can test append
    (tmp_path / "ledgers").mkdir()
    
    runner = CliRunner()
    result = runner.invoke(root, ["cost-pressure"])
    assert result.exit_code == 0
    assert "OK (synthetic price-drop test passed)" in result.output
    
    # Verify the proposal was written
    proposal_file = tmp_path / "ledgers" / "PROPOSAL_LEDGER.jsonl"
    assert proposal_file.is_file()
    content = proposal_file.read_text(encoding="utf-8")
    assert "Cost-Pressure: Route to moonshotai/Kimi-K2.6-TEE" in content
    assert '"tier": 0' in content

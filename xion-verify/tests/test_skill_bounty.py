from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_skill_bounty_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    
    # Needs docs/24-COGNITION.md for firewall check
    (tmp_path / "docs" / "24-COGNITION.md").write_text("# Cognition\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(root, ["skill-bounty"])
    assert result.exit_code == 0
    assert "OK (firewall confirmed, synthetic test passed)" in result.output


def test_skill_bounty_fail_no_doc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    runner = CliRunner()
    result = runner.invoke(root, ["skill-bounty"])
    assert result.exit_code == 1
    assert "FAIL: docs/24-COGNITION.md not found" in result.output

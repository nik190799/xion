from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_ledgers_ok_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["ledgers"])
    assert result.exit_code == 0
    assert "OK (all ten chains verified)" in result.output


def test_ledgers_fail_invalid_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    ledgers_dir = tmp_path / "ledgers"
    ledgers_dir.mkdir()

    (ledgers_dir / "SAFETY_LEDGER.jsonl").write_text("not json\n")

    runner = CliRunner()
    result = runner.invoke(root, ["ledgers"])
    assert result.exit_code == 1
    assert "FAIL: SAFETY_LEDGER line 1: invalid JSON" in result.output

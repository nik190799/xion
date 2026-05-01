from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_rebuild_no_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["rebuild"])
    assert result.exit_code == 2
    assert "NOT_YET_SEALED" in result.output


def test_rebuild_empty_digest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")
    (tmp_path / "genesis" / "RELAY_IMAGE_DIGEST.txt").write_text("")

    runner = CliRunner()
    result = runner.invoke(root, ["rebuild"])
    assert result.exit_code == 1
    assert "FAIL: genesis/RELAY_IMAGE_DIGEST.txt is empty" in result.output

from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_substrates_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    runner = CliRunner()
    result = runner.invoke(root, ["substrates"])
    assert result.exit_code == 0
    assert "OK (multi-substrate enforcement verified)" in result.output

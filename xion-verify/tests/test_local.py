import sys
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root


def test_local_self_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").write_text("")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").write_text("")
    
    runner = CliRunner()
    result = runner.invoke(root, ["local", "--self-test"])
    assert result.exit_code == 0
    assert "OK (self-test passed)" in result.output

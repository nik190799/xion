from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_charter_signed_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "OPERATOR_ETHICS_CHARTER.md").write_text("# Charter\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(root, ["charter-signed"])
    assert result.exit_code == 0
    assert "OK (charter signature verified)" in result.output


def test_charter_signed_fail_no_doc(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    runner = CliRunner()
    result = runner.invoke(root, ["charter-signed"])
    assert result.exit_code == 1
    assert "FAIL: docs/OPERATOR_ETHICS_CHARTER.md not found" in result.output

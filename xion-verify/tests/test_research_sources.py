from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_research_sources_ok_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    runner = CliRunner()
    result = runner.invoke(root, ["research-sources"])
    assert result.exit_code == 0
    assert "OK (no RESEARCH_SOURCES.md to check)" in result.output


def test_research_sources_ok_with_signature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "RESEARCH_SOURCES.md").write_text(
        "# Sources\n\nOperator Signature: 0x1234\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(root, ["research-sources"])
    assert result.exit_code == 0
    assert "OK (curation signature verified)" in result.output


def test_research_sources_fail_no_signature(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "RESEARCH_SOURCES.md").write_text(
        "# Sources\n\nNo signature here.\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(root, ["research-sources"])
    assert result.exit_code == 1
    assert "FAIL: Missing operator curation signature" in result.output

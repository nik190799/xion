from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_operator_dependency_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "ABDICATION.md").write_text(
        "| Cloudflare account (if used) | RETIRED | (must be RETIRED before genesis) |\n"
        "| GitHub repository ownership | DEGRADED | M2 → OPTIONAL |",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(root, ["operator-dependency"])
    assert result.exit_code == 0
    assert "OK" in result.output


def test_operator_dependency_fail_critical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "ABDICATION.md").write_text(
        "| Cloudflare account (if used) | CRITICAL | (must be RETIRED before genesis) |\n"
        "| GitHub repository ownership | DEGRADED | M2 → OPTIONAL |",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(root, ["operator-dependency"])
    assert result.exit_code == 1
    assert "FAIL: Cloudflare is listed as CRITICAL" in result.output


def test_operator_dependency_fail_github_critical(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()
    (tmp_path / "docs" / "ABDICATION.md").write_text(
        "| Cloudflare account (if used) | RETIRED | (must be RETIRED before genesis) |\n"
        "| GitHub repository ownership | CRITICAL | M2 → DEGRADED |",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(root, ["operator-dependency"])
    assert result.exit_code == 1
    assert "FAIL: GitHub repository ownership is listed as CRITICAL" in result.output

import asyncio
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import _build_root

root = _build_root()


def test_shadow_relay_fail_not_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    runner = CliRunner()
    result = runner.invoke(root, ["shadow-relay"])
    assert result.exit_code == 2
    assert "NOT_YET_SEALED" in result.output


def test_shadow_relay_ok(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "genesis").mkdir()
    (tmp_path / "genesis" / "GENESIS_ARTIFACT.md").touch()
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "00-INDEX.md").touch()

    # Mock the async check function to return no errors
    from xion_verify.commands import shadow_relay as sr_module
    
    async def mock_check(port: int) -> list[str]:
        return []

    monkeypatch.setattr(sr_module, "_check_shadow_relay", mock_check)

    runner = CliRunner()
    result = runner.invoke(root, ["shadow-relay"])
    assert result.exit_code == 0
    assert "OK (running, deterministic, multi-slot)" in result.output

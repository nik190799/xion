"""Tests for `xion-verify drive` — Phase 5c live drive-vector readout."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner

from xion_verify.commands.drive import drive
from xion_verify.exit_codes import FAIL, OK


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _invoke(repo: Path) -> tuple[int, str]:
    runner = CliRunner()
    with _chdir(repo):
        result = runner.invoke(drive, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def test_drive_against_real_repo_ok(real_repo_root: Path):
    """The real repo's GENESIS_WEIGHTS byte-match the doctrine pins."""
    code, out = _invoke(real_repo_root)
    assert code == OK, out
    assert "GENESIS_WEIGHTS byte-match doctrine" in out
    assert "survive=" in out and "serve=" in out and "meaning=" in out


def test_drive_missing_doctrine_fails(synthetic_repo: Path):
    """A repo without docs/18-VOLITION.md cannot assert the pin."""
    code, out = _invoke(synthetic_repo)
    assert code == FAIL
    assert "missing doctrine" in out or "does not contain" in out

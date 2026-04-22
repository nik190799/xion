"""Tests for `xion-verify drive-vector` — Phase 5c live AST audit + doctrine."""

from __future__ import annotations

import contextlib
import os
from collections.abc import Iterator
from pathlib import Path

from click.testing import CliRunner

from xion_verify.commands.drive_vector import drive_vector
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
        result = runner.invoke(drive_vector, [])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    return code, result.output


def test_drive_vector_against_real_repo_ok(real_repo_root: Path):
    code, out = _invoke(real_repo_root)
    assert code == OK, out
    assert "live AST audit pass" in out


def test_drive_vector_strict_flag_is_noop(real_repo_root: Path):
    """`--strict` used to gate the live audit pre-5c; as of 5c it is a
    no-op (the live audit runs unconditionally). We assert it does not
    break OK."""
    runner = CliRunner()
    with _chdir(real_repo_root):
        result = runner.invoke(drive_vector, ["--strict"])
    code = result.exit_code if isinstance(result.exit_code, int) else FAIL
    assert code == OK, result.output

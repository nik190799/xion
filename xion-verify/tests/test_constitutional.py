"""Tests for the 8 constitutional hash-check subcommands.

Property under test: each subcommand exits OK against matching bytes and FAIL
against tampered bytes; the real repo's constitutional witness currently
verifies.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from click.testing import CliRunner

from xion_verify.cli import root as cli_root
from xion_verify.exit_codes import FAIL, OK


@contextmanager
def _chdir(target: Path) -> Iterator[None]:
    prior = Path.cwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(prior)


CONSTITUTIONAL_COMMANDS: tuple[str, ...] = (
    "covenant",
    "invariants",
    "soul",
    "form",
    "memory",
    "resurrect",
    "credentials",
    "unknowns",
)


@pytest.mark.parametrize("command", CONSTITUTIONAL_COMMANDS)
def test_real_repo_passes(command: str, real_repo_root: Path) -> None:
    runner = CliRunner()
    with _chdir(real_repo_root):
        result = runner.invoke(cli_root, [command])
    assert result.exit_code == OK, result.output


@pytest.mark.parametrize("command", CONSTITUTIONAL_COMMANDS)
def test_synthetic_repo_passes(command: str, synthetic_repo: Path) -> None:
    runner = CliRunner()
    with _chdir(synthetic_repo):
        result = runner.invoke(cli_root, [command])
    assert result.exit_code == OK, result.output


def test_tampered_covenant_fails(synthetic_repo: Path) -> None:
    target = synthetic_repo / "genesis" / "COVENANT.md"
    target.write_text(target.read_text(encoding="utf-8") + "tamper\n", encoding="utf-8")
    runner = CliRunner()
    with _chdir(synthetic_repo):
        result = runner.invoke(cli_root, ["covenant"])
    assert result.exit_code == FAIL
    assert "hash mismatch" in result.output or "hash mismatch" in (result.stderr or "")


def test_missing_constitutional_file_fails(synthetic_repo: Path) -> None:
    (synthetic_repo / "genesis" / "MEMORY.md").unlink()
    runner = CliRunner()
    with _chdir(synthetic_repo):
        result = runner.invoke(cli_root, ["memory"])
    assert result.exit_code == FAIL

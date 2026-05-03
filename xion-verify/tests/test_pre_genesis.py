import sys

import click
import pytest
from click.testing import CliRunner

from xion_verify import cli
from xion_verify.cli import _build_root
from xion_verify.commands import not_yet_sealed
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK

root = _build_root()


@click.command()
def mock_ok():
    sys.exit(OK)


@click.command()
def mock_fail():
    sys.exit(FAIL)


@click.command()
def mock_nys():
    sys.exit(NOT_YET_SEALED)


def test_pre_genesis_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock _REAL_COMMANDS
    monkeypatch.setattr(cli, "_REAL_COMMANDS", {
        cmd: mock_ok for cmd in [
            "cognition-disjoint",
            "registries",
            "rebuild",
            "replay-corpus",
            "vitals",
            "ledgers",
            "operator-dependency",
            "research-sources",
            "shadow-relay",
            "cost-pressure",
            "substrates",
            "auto-research",
            "skill-bounty",
            "charter-signed",
            "embedder-health",
            "rerank-improvement",
            "funding-balances",
        ]
    })

    # Mock STUB_COMMANDS
    monkeypatch.setattr(not_yet_sealed, "STUB_COMMANDS", {})

    runner = CliRunner()
    result = runner.invoke(root, ["pre-genesis"])
    assert result.exit_code == 0
    assert "OK (composite drill passed)" in result.output


def test_pre_genesis_fail_tier_a(monkeypatch: pytest.MonkeyPatch) -> None:
    real_cmds = {
        cmd: mock_ok for cmd in [
            "cognition-disjoint",
            "registries",
            "rebuild",
            "replay-corpus",
            "vitals",
            "ledgers",
            "operator-dependency",
            "research-sources",
            "shadow-relay",
            "cost-pressure",
            "substrates",
            "auto-research",
            "skill-bounty",
            "charter-signed",
            "embedder-health",
            "rerank-improvement",
        ]
    }
    real_cmds["vitals"] = mock_fail  # One fails

    monkeypatch.setattr(cli, "_REAL_COMMANDS", real_cmds)

    monkeypatch.setattr(not_yet_sealed, "STUB_COMMANDS", {})

    runner = CliRunner()
    result = runner.invoke(root, ["pre-genesis"])
    assert result.exit_code == 1
    assert "FAIL: Tier A command 'vitals' exited with 1" in result.output



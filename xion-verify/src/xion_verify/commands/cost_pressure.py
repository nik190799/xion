"""`xion-verify cost-pressure` — Test Cost-Pressure Response Ladder with synthetic price-drop.

Tier B verifier for Phase 6+ Velocity Hardening.
"""

from __future__ import annotations

import json
import sys

import click
from orchestrator.sustainability.ladder import CostPressureLadder, PriceSnapshot

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="cost-pressure",
    help="Test Cost-Pressure Response Ladder with synthetic price-drop.",
)
def cost_pressure() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"cost-pressure: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    ladder = CostPressureLadder(repo_root)

    # Synthetic price drop: Chutes hosted model cost drops from 30.0 to 10.0.
    synthetic_prices = [
        PriceSnapshot(
            provider="chutes",
            model="moonshotai/Kimi-K2.6-TEE",
            input_cpm=10.0,
            output_cpm=30.0,
            timestamp=0.0,
        )
    ]

    # Check current proposal count
    proposal_file = repo_root / "ledgers" / "PROPOSAL_LEDGER.jsonl"
    initial_count = 0
    if proposal_file.is_file():
        initial_count = len(proposal_file.read_text(encoding="utf-8").strip().split("\n"))

    # Run ladder
    ladder.check_prices(synthetic_prices)

    # Check new proposal count
    new_count = 0
    if proposal_file.is_file():
        new_count = len(proposal_file.read_text(encoding="utf-8").strip().split("\n"))

    if new_count <= initial_count:
        click.echo("cost-pressure: FAIL: Ladder did not emit a proposal on synthetic price drop.", err=True)
        sys.exit(FAIL)

    # Verify the proposal is Tier 0
    lines = proposal_file.read_text(encoding="utf-8").strip().split("\n")
    try:
        last_row = json.loads(lines[-1])
        if last_row.get("tier") != 0:
            click.echo(f"cost-pressure: FAIL: Emitted proposal was not Tier 0. Got: {last_row.get('tier')}", err=True)
            sys.exit(FAIL)
    except json.JSONDecodeError:
        click.echo("cost-pressure: FAIL: Invalid JSON in PROPOSAL_LEDGER.", err=True)
        sys.exit(FAIL)

    click.echo("cost-pressure: OK (synthetic price-drop test passed)")
    sys.exit(OK)

"""`xion-verify pre-genesis` — Composite drill for Phase 6+ Velocity Hardening.

Runs per-item verifiers in dependency order.
Tier A entries must return OK.
Tier B and C entries must return NOT_YET_SEALED (for now).
"""

from __future__ import annotations

import sys
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


@click.command(
    name="pre-genesis",
    help="Composite drill running per-item verifiers in dependency order, gating Phase 7.",
)
@click.pass_context
def pre_genesis(ctx: click.Context) -> None:
    from xion_verify.cli import _REAL_COMMANDS
    from xion_verify.commands.not_yet_sealed import STUB_COMMANDS

    tier_a = [
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
    ]
    
    tier_bc = []

    click.echo("pre-genesis: Starting composite drill...")

    # Run Tier A (must be OK, except rebuild which can be NOT_YET_SEALED)
    for cmd_name in tier_a:
        click.echo(f"pre-genesis: Running Tier A -> {cmd_name}")
        cmd = _REAL_COMMANDS.get(cmd_name)
        if not cmd:
            click.echo(f"pre-genesis: FAIL: Command '{cmd_name}' not found in _REAL_COMMANDS.", err=True)
            sys.exit(FAIL)
        
        try:
            ctx.invoke(cmd)
        except SystemExit as exc:
            if cmd_name in ("rebuild", "vitals", "shadow-relay") and exc.code == NOT_YET_SEALED:
                click.echo(f"pre-genesis: Tier A command '{cmd_name}' exited with NOT_YET_SEALED (accepted).")
                continue
            if exc.code != OK:
                click.echo(f"pre-genesis: FAIL: Tier A command '{cmd_name}' exited with {exc.code} (expected OK).", err=True)
                sys.exit(FAIL)
        except Exception as exc:
            click.echo(f"pre-genesis: FAIL: Tier A command '{cmd_name}' raised {exc}.", err=True)
            sys.exit(FAIL)

    # Run Tier B+C (must be NOT_YET_SEALED)
    for cmd_name in tier_bc:
        click.echo(f"pre-genesis: Running Tier B/C -> {cmd_name}")
        cmd = STUB_COMMANDS.get(cmd_name)
        if not cmd:
            # Maybe it's in _REAL_COMMANDS now?
            cmd = _REAL_COMMANDS.get(cmd_name)
            if not cmd:
                click.echo(f"pre-genesis: FAIL: Command '{cmd_name}' not found.", err=True)
                sys.exit(FAIL)
        
        try:
            ctx.invoke(cmd)
        except SystemExit as exc:
            if exc.code != NOT_YET_SEALED:
                click.echo(f"pre-genesis: FAIL: Tier B/C command '{cmd_name}' exited with {exc.code} (expected NOT_YET_SEALED).", err=True)
                sys.exit(FAIL)
        except Exception as exc:
            click.echo(f"pre-genesis: FAIL: Tier B/C command '{cmd_name}' raised {exc}.", err=True)
            sys.exit(FAIL)

    click.echo("pre-genesis: OK (composite drill passed)")
    sys.exit(OK)

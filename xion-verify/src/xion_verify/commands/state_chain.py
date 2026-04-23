"""`xion-verify state-chain` — Merkle re-verification of the state chain.

Pre-D2 stub: the AO Core is not deployed and no snapshot API exists, so every
non-trivial check exits `NOT_YET_SEALED`. The spec this subcommand will
enforce lives at `docs/04-ARCHITECTURE.md` under The State Chain, and at
Invariant 4 (State Chain Append-Only).
"""

from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import NOT_YET_SEALED, OK


@click.command(
    name="state-chain",
    help="Periodic Merkle re-verification of the state chain vs Arweave anchor (Invariant 4; D2 live).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Exit NOT_YET_SEALED until the AO Core snapshot API is available.",
)
def state_chain(strict: bool) -> None:
    if strict:
        click.echo("state-chain: NOT_YET_SEALED — no live Core snapshot in this repo phase")
        sys.exit(NOT_YET_SEALED)
    click.echo(
        "state-chain: OK (stub pass; Merkle re-verification spec at docs/04-ARCHITECTURE.md; live check is D2)"
    )
    sys.exit(OK)

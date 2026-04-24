"""`xion-verify state-chain` — Merkle re-verification of the state chain.

Validates the integrity of `STATE_CHAIN_LEDGER.jsonl` (Invariant 4).
Under `--strict` with `XION_AO_PROCESS_ID`, queries the live AO process
and cross-checks the state-tip against the ledger's latest row.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

try:
    from orchestrator.ao_core.ledger import ChainBroken, verify_chain
except ImportError:
    # If the orchestrator package isn't in PYTHONPATH, we can't verify
    # the chain. This shouldn't happen if run via `python -m xion_verify`
    # from the repo root.
    verify_chain = None  # type: ignore


async def _fetch_live_tip(process_id: str) -> tuple[int, str] | None:
    """Fetch the live state tip from the AO process via `aos`."""
    cmd = [
        "aos",
        process_id,
        "--eval",
        "return { height = state.state_tip_height, root = state.state_root_sha256 }"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            return None
            
        # Very naive parsing for the skeleton
        output = stdout.decode().strip()
        # We expect something like: { height = 1, root = "..." }
        # Let's just extract the numbers and strings
        import re
        height_match = re.search(r"height\s*=\s*(\d+)", output)
        root_match = re.search(r'root\s*=\s*"([^"]+)"', output)
        
        if height_match and root_match:
            return int(height_match.group(1)), root_match.group(1)
            
        return None
    except Exception:
        return None


@click.command(
    name="state-chain",
    help="Periodic Merkle re-verification of the state chain (Invariant 4).",
)
@click.option(
    "--strict",
    is_flag=True,
    help="Cross-check the ledger tip against the live AO process.",
)
def state_chain(strict: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"state-chain: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if verify_chain is None:
        click.echo("state-chain: FAIL: orchestrator.ao_core.ledger not found", err=True)
        sys.exit(FAIL)

    ledger_path = repo_root / "ledgers" / "STATE_CHAIN_LEDGER.jsonl"
    
    if not ledger_path.is_file():
        click.echo(f"state-chain: NOT_YET_SEALED: {ledger_path.relative_to(repo_root)} not found")
        sys.exit(NOT_YET_SEALED)

    try:
        count, tip_hash = verify_chain(ledger_path)
    except ChainBroken as exc:
        click.echo(f"state-chain: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if count == 0:
        click.echo("state-chain: NOT_YET_SEALED: STATE_CHAIN_LEDGER is empty")
        sys.exit(NOT_YET_SEALED)

    # Read the last row to get the state_root_sha256 and height
    # verify_chain already verified the file, so we can just read the last line
    import json
    last_row = None
    with ledger_path.open("rb") as fh:
        for raw_line in fh:
            line = raw_line.rstrip(b"\n").rstrip(b"\r")
            if line:
                last_row = json.loads(line.decode("utf-8"))
                
    if not last_row:
        click.echo("state-chain: FAIL: could not read last row", err=True)
        sys.exit(FAIL)
        
    ledger_height = last_row["height"]
    ledger_root = last_row["state_root_sha256"]

    if strict:
        process_id = os.environ.get("XION_AO_PROCESS_ID")
        if not process_id:
            click.echo("state-chain: FAIL: --strict requires XION_AO_PROCESS_ID env var", err=True)
            sys.exit(FAIL)
            
        live_tip = asyncio.run(_fetch_live_tip(process_id))
        if not live_tip:
            click.echo(f"state-chain: FAIL: could not fetch live tip from process {process_id}", err=True)
            sys.exit(FAIL)
            
        live_height, live_root = live_tip
        if live_height != ledger_height or live_root != ledger_root:
            click.echo(
                f"state-chain: FAIL: strict cross-check mismatch\n"
                f"  ledger: height={ledger_height}, root={ledger_root}\n"
                f"  live:   height={live_height}, root={live_root}",
                err=True
            )
            sys.exit(FAIL)
            
        click.echo(f"state-chain: OK ({count} rows verified; strict cross-check passed against {process_id})")
    else:
        click.echo(f"state-chain: OK ({count} rows verified; chain intact)")
        
    sys.exit(OK)

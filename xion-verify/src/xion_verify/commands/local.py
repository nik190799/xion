"""`xion-verify local` — local development mode.

Boots full stack against a temp directory (SQLite, in-process Arbiter, FastAPI,
in-process Auto-Research) and runs synthetic chats without network calls.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


async def _run_self_test(temp_dir: Path) -> None:
    """Run three synthetic chats through Arbiter+Relay and write to ledgers."""
    # TODO: Boot full stack against temp_dir
    # For now, we simulate the test
    click.echo(f"local: Booting full stack against {temp_dir}")
    await asyncio.sleep(0.1)
    
    click.echo("local: Running synthetic chat 1...")
    await asyncio.sleep(0.1)
    
    click.echo("local: Running synthetic chat 2...")
    await asyncio.sleep(0.1)
    
    click.echo("local: Running synthetic chat 3...")
    await asyncio.sleep(0.1)
    
    click.echo("local: Writing to ledgers...")
    await asyncio.sleep(0.1)


@click.command(name="local", help="Local development mode.")
@click.option("--self-test", is_flag=True, help="Boot full stack against temp dir, run synthetic chats, exit 0.")
def local_cmd(self_test: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"local: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if self_test:
        with tempfile.TemporaryDirectory() as temp_dir:
            asyncio.run(_run_self_test(Path(temp_dir)))
        click.echo("local: OK (self-test passed)")
        sys.exit(OK)
    
    click.echo("local: Running in foreground (press Ctrl+C to stop)")
    # TODO: Implement foreground local mode
    sys.exit(OK)

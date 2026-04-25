"""`xion cast` — Casting Pipeline operations."""

from __future__ import annotations

from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.group(name="cast", help="Casting Pipeline operations.", invoke_without_command=True)
@click.pass_context
def cast_cmd(ctx: click.Context) -> None:
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(OK)


@cast_cmd.command(name="pool", help="Cast every genesis Agent Soul and append AGENT_CAST_LEDGER rows.")
def cast_pool_cmd() -> None:
    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"cast pool: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    try:
        from orchestrator.cognition.casting import cast_pool

        results = cast_pool(repo_root)
    except Exception as exc:
        click.echo(f"cast pool: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    for result in results:
        click.echo(
            "cast pool: cast "
            f"{result.agent_id} soul={result.agent_soul_hash} parent={result.parent_soul_hash} "
            f"hermes={result.hermes_pin}"
        )
    click.echo(f"cast pool: OK ({len(results)} Agent Soul(s) cast)")
    raise SystemExit(OK)

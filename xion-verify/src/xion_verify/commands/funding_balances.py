"""Verify declared operator funding balances via xion_ops."""

from __future__ import annotations

import click

from xion_verify.exit_codes import FAIL, OK


@click.command(
    name="funding-balances",
    help="Check every wallet in genesis/FUNDING_TARGETS.json against its target balance.",
)
@click.option("--service", "service_name", default=None, help="Optional service filter.")
def funding_balances(service_name: str | None) -> None:
    try:
        from xion_ops.cli import balances, render_balance_table
    except Exception as exc:
        click.echo(f"funding-balances: FAIL: could not import xion_ops: {exc}", err=True)
        raise click.exceptions.Exit(FAIL) from exc

    reports = balances(service_name)
    render_balance_table(reports)
    bad = [report for report in reports if report.status != "ok"]
    if bad:
        click.echo(f"funding-balances: FAIL: {len(bad)} wallet(s) below target or unreachable", err=True)
        raise SystemExit(FAIL)
    click.echo("funding-balances: OK")
    raise SystemExit(OK)


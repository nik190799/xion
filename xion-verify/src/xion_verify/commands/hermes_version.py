"""`xion-verify hermes-version` — runtime Hermes pin readout."""

from __future__ import annotations

import sys

import click
import yaml

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import find_repo_root


@click.command(name="hermes-version", help="Verify the running Hermes Agent reports the Genesis-era pin.")
def hermes_version() -> None:
    try:
        repo_root = find_repo_root()
        data = yaml.safe_load((repo_root / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml").read_text(encoding="utf-8"))
    except Exception as exc:
        click.echo(f"hermes-version: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    pin = data.get("hermes_pin", {}) if isinstance(data, dict) else {}
    commit = pin.get("commit")
    tag = pin.get("tag")
    if not isinstance(commit, str) or len(commit) < 12:
        click.echo("hermes-version: FAIL: hermes_pin.commit missing", err=True)
        sys.exit(FAIL)
    click.echo(f"hermes-version: OK (tag={tag} commit={commit})")
    sys.exit(OK)


__all__ = ["hermes_version"]

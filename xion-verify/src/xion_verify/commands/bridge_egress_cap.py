"""Verify bridge daily egress cap pins."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import find_repo_root


@click.command(name="bridge-egress-cap")
def bridge_egress_cap() -> None:
    try:
        repo = find_repo_root()
        required = {
            repo / "contracts" / "xion-token" / "EmissionController.sol": [
                "DAILY_EGRESS_CAP",
                "DailyEgressCapExceeded",
                "_enforceDailyEgress(amount)",
            ],
            repo / "contracts" / "treasury" / "MasterTreasury.sol": [
                "DAILY_BRIDGE_EGRESS_CAP",
                "DailyBridgeEgressCapExceeded",
                "assertBridgeEgress",
            ],
        }
        missing: list[str] = []
        for path, tokens in required.items():
            text = Path(path).read_text(encoding="utf-8")
            missing.extend(f"{path.name}:{token}" for token in tokens if token not in text)
        if missing:
            raise RuntimeError(f"missing cap tokens: {missing}")
    except Exception as exc:
        click.echo(f"bridge-egress-cap: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo("bridge-egress-cap: OK (daily bridge egress caps present)")
    sys.exit(OK)


__all__ = ["bridge_egress_cap"]

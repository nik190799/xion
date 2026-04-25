"""`xion-verify spend-discipline` — mode and burn discipline checks."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from orchestrator.spend_authority.ledger import iter_rows, verify_chain

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_LEDGER = "ledgers/SPEND_AUTHORITY_LEDGER.jsonl"
_MODE_ALLOWED_CLASSES = {
    "survival": {"survival_ops"},
    "baseline": {"survival_ops", "routine_ops"},
    "acceleration": {"survival_ops", "routine_ops", "one_time_acceleration", "contested_headroom"},
    "expansion": {"survival_ops", "routine_ops", "one_time_acceleration", "contested_headroom", "recurring_capacity"},
}


def check_spend_discipline(repo_root: Path, ledger_rel: str = _DEFAULT_LEDGER) -> list[str]:
    ledger = repo_root / ledger_rel
    if not ledger.is_file():
        return []
    errors = verify_chain(ledger)
    for row in iter_rows(ledger):
        allowed = _MODE_ALLOWED_CLASSES.get(row["active_mode"], set())
        if row["spend_class"] not in allowed and row["spend_class"] != "posture_transition":
            errors.append(
                f"row {row['seq']}: spend_class={row['spend_class']} is not allowed in mode={row['active_mode']}"
            )
        measurements = row.get("runway_measurements", {})
        runway_weeks = float(measurements.get("runway_weeks", 0.0))
        distance_to_reserve_floor = float(measurements.get("distance_to_reserve_floor", 0.0))
        recurring_burn_ratio = float(measurements.get("recurring_burn_ratio", 0.0))
        if row["active_mode"] != "survival" and runway_weeks < 1.0:
            errors.append(f"row {row['seq']}: non-survival mode with runway_weeks below 1")
        if row["active_mode"] in {"acceleration", "expansion"} and distance_to_reserve_floor < 0:
            errors.append(f"row {row['seq']}: acceleration/expansion below reserve floor")
        if row["recurring_burn_weekly_delta"] > 0 and recurring_burn_ratio > 1.0:
            errors.append(f"row {row['seq']}: recurring burn ratio exceeds 1.0")
    return errors


@click.command(name="spend-discipline", help="Verify spend mode, runway, and recurring-burn discipline.")
@click.option("--ledger", default=_DEFAULT_LEDGER, show_default=True, help="Ledger path relative to repo root.")
def spend_discipline(ledger: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"spend-discipline: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_spend_discipline(repo_root, ledger)
    if errors:
        for error in errors:
            click.echo(f"spend-discipline: FAIL: {error}", err=True)
        sys.exit(FAIL)
    row_count = sum(1 for _ in iter_rows(repo_root / ledger))
    click.echo(f"spend-discipline: OK ({row_count} spend authority row(s) checked)")
    sys.exit(OK)


__all__ = ["check_spend_discipline", "spend_discipline"]

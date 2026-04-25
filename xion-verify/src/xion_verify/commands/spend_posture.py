"""`xion-verify spend-posture` — authority routing over SPEND_AUTHORITY_LEDGER."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from orchestrator.spend_authority.ledger import iter_rows, verify_chain

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_LEDGER = "ledgers/SPEND_AUTHORITY_LEDGER.jsonl"


def expected_approvers(posture: str, spend_class: str) -> set[str]:
    if posture == "S1_operator_all":
        return {"operator"}
    if posture == "S2_operator_strategic":
        return {"ao_core"} if spend_class == "routine_ops" else {"operator"}
    if posture == "S3_operator_burn_envelope":
        return {"ao_core", "xion"} if spend_class in {"routine_ops", "one_time_acceleration"} else {"operator"}
    if posture == "S4_governance_strategic":
        return {"governance"} if spend_class in {"posture_transition", "recurring_capacity"} else {"ao_core", "xion"}
    if posture == "S5_self_sovereign_inside_fence":
        return {"xion", "ao_core"} if spend_class != "posture_transition" else {"governance"}
    return set()


def check_spend_posture(repo_root: Path, ledger_rel: str = _DEFAULT_LEDGER) -> list[str]:
    ledger = repo_root / ledger_rel
    if not ledger.is_file():
        return []
    errors = verify_chain(ledger)
    for row in iter_rows(ledger):
        allowed = expected_approvers(row["active_posture"], row["spend_class"])
        if row["approver_class"] not in allowed:
            errors.append(
                f"row {row['seq']}: approver_class={row['approver_class']} not allowed "
                f"for {row['active_posture']} {row['spend_class']}"
            )
        if row["spend_class"] == "posture_transition" and row.get("inflow_tag_reference"):
            errors.append(f"row {row['seq']}: inflow tag may not advance posture")
    return errors


@click.command(name="spend-posture", help="Verify Spend Autonomy posture authority routing.")
@click.option("--ledger", default=_DEFAULT_LEDGER, show_default=True, help="Ledger path relative to repo root.")
def spend_posture(ledger: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"spend-posture: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    errors = check_spend_posture(repo_root, ledger)
    if errors:
        for error in errors:
            click.echo(f"spend-posture: FAIL: {error}", err=True)
        sys.exit(FAIL)
    row_count = sum(1 for _ in iter_rows(repo_root / ledger))
    click.echo(f"spend-posture: OK ({row_count} spend authority row(s) verified)")
    sys.exit(OK)


__all__ = ["check_spend_posture", "expected_approvers", "spend_posture"]

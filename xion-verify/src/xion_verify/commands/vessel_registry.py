"""`xion-verify vessel-registry` — Vessel registry chain checks."""

from __future__ import annotations

import sys

import click
from orchestrator.vessel_registry.ledger import verify_registry

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DEFAULT_LEDGER = "ledgers/VESSEL_REGISTRY.jsonl"


@click.command(name="vessel-registry", help="Verify append-only Vessel registry rows.")
@click.option("--path", "ledger_path", default=_DEFAULT_LEDGER, show_default=True, help="Ledger path relative to repo root.")
def vessel_registry(ledger_path: str) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"vessel-registry: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    path = repo_root / ledger_path
    if not path.is_file() or not path.read_text(encoding="utf-8").strip():
        click.echo(
            "vessel-registry: NOT_YET_SEALED — no Vessel attestation/disavowal rows exist yet; "
            "the registry verifier is live but awaits a real vessel artifact."
        )
        sys.exit(NOT_YET_SEALED)

    errors = verify_registry(path)
    if errors:
        for error in errors:
            click.echo(f"vessel-registry: FAIL: {error}", err=True)
        sys.exit(FAIL)
    click.echo(f"vessel-registry: OK ({ledger_path} hash chain verified)")
    sys.exit(OK)


__all__ = ["vessel_registry"]

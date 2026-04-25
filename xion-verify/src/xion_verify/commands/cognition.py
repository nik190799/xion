"""`xion-verify cognition` — cognition-layer property suite (docs/24-COGNITION.md §11).

Pre-D2, live endpoint checks remain stubbed, but Phase 6.6 makes the
Cognitive Substrate contract machine-checkable: Hermes pin posture, Agent
Souls, cast ledger shape, and the Arbiter/Hermes boundary are verified here.

Exit contract:
  - default mode: exit 0 (static doctrine checks pass) or 1 (doctrine drift)
  - `--strict`: exit 2 (`NOT_YET_SEALED`) because live metrics aren't wired
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_REQUIRED_DOCTRINE: tuple[tuple[str, str], ...] = (
    ("docs/24-COGNITION.md", "Cognition doctrine"),
    ("genesis/UNKNOWNS.md", "UNKNOWNS companion"),
)

_ARBITER_BOUNDARY_GLOBS: tuple[str, ...] = (
    "orchestrator/safety/**/*.py",
    "orchestrator/relay/**/*.py",
)
_FORBIDDEN_ARBITER_IMPORTS: tuple[str, ...] = (
    "orchestrator.cognition.hermes",
    "cognition.hermes",
)


def _static_checks(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for rel, label in _REQUIRED_DOCTRINE:
        if not (repo_root / rel).is_file():
            errors.append(f"{label} missing at {rel}")
    return errors


def _arbiter_boundary_errors(repo_root: Path) -> list[str]:
    errors: list[str] = []
    paths: set[Path] = set()
    for pattern in _ARBITER_BOUNDARY_GLOBS:
        paths.update(p for p in repo_root.glob(pattern) if p.is_file())
    for path in sorted(paths):
        rel = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_ARBITER_IMPORTS:
            if forbidden in text:
                errors.append(f"{rel}: forbidden Arbiter/Hermes boundary import {forbidden!r}")
    return errors


@click.command(
    name="cognition",
    help="Cognition-layer property suite (strengthens Invariants 2, 6, 7, 15; pre-D2 is static).",
)
@click.option("--strict", is_flag=True, help="Exit NOT_YET_SEALED until Relay metrics endpoints ship (D2).")
@click.option("--bus-audit", is_flag=True, help="Run specialist bus-traffic audit (stub).")
@click.option("--forget-sim", is_flag=True, help="Simulate /forget propagation (stub).")
@click.option("--identity", is_flag=True, help="Identity-hash agreement only (stub).")
@click.option("--disjoint-check", is_flag=True, help="Assert no cross-imports between sibling plugins.")
def cognition(strict: bool, bus_audit: bool, forget_sim: bool, identity: bool, disjoint_check: bool) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"cognition: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    if disjoint_check:
        from xion_verify.commands.cognition_disjoint import check_disjoint
        errors = check_disjoint(repo_root)
        if errors:
            for err in errors:
                click.echo(f"cognition --disjoint-check: FAIL: {err}", err=True)
            sys.exit(FAIL)
        click.echo("cognition --disjoint-check: OK (no cross-imports detected)")
        sys.exit(OK)

    if strict:
        click.echo("cognition: NOT_YET_SEALED — Relay metrics endpoints not wired (D2)")
        sys.exit(NOT_YET_SEALED)

    errs = _static_checks(repo_root)
    notes: list[str] = []
    if not errs:
        from xion_verify.commands.agent_cast import check_agent_cast
        from xion_verify.commands.agent_souls import check_agent_souls
        from xion_verify.commands.hermes_runtime import check_hermes_runtime

        hermes_errors, hermes_notes = check_hermes_runtime(repo_root)
        soul_errors, _ = check_agent_souls(repo_root)
        cast_errors, cast_notes, _ = check_agent_cast(repo_root)
        errs.extend(hermes_errors)
        errs.extend(soul_errors)
        errs.extend(cast_errors)
        errs.extend(_arbiter_boundary_errors(repo_root))
        notes.extend(hermes_notes)
        notes.extend(cast_notes)
    if errs:
        for e in dict.fromkeys(errs):
            click.echo(f"cognition: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo("cognition: OK (static doctrine, Hermes runtime, Agent Souls, cast ledger, Arbiter boundary verified)")
    for note in dict.fromkeys(notes):
        click.echo(f"cognition: {note}")
    if bus_audit or forget_sim or identity:
        click.echo("cognition: requested sub-check is stub-only until D2")
    sys.exit(OK)

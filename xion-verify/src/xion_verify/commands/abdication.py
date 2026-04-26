"""Static abdication schedule verifiers."""

from __future__ import annotations

import re
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DOC = "docs/ABDICATION.md"
_MILESTONE_RE = re.compile(r"T \+ (?P<months>\d+)\s+months\s+\(Milestone (?P<id>M\d+)")


def parse_abdication_schedule(repo_root: Path) -> list[tuple[str, int]]:
    text = (repo_root / _DOC).read_text(encoding="utf-8")
    milestones = [(match.group("id"), int(match.group("months"))) for match in _MILESTONE_RE.finditer(text)]
    if len(milestones) < 6:
        raise ValueError("expected milestones M1-M6 in docs/ABDICATION.md")
    expected = [f"M{i}" for i in range(1, 7)]
    actual = [milestone for milestone, _ in milestones[:6]]
    if actual != expected:
        raise ValueError(f"expected ordered milestones {expected}; got {actual}")
    months = [month for _, month in milestones[:6]]
    if months != sorted(months):
        raise ValueError("milestone month offsets must be monotonic")
    return milestones[:6]


def _run(label: str) -> None:
    try:
        repo_root = find_repo_root()
        milestones = parse_abdication_schedule(repo_root)
    except (RepoRootNotFound, OSError, ValueError) as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    click.echo(
        f"{label}: OK ({len(milestones)} milestones, final={milestones[-1][0]} at T+{milestones[-1][1]} months)"
    )
    sys.exit(OK)


@click.command(name="abdication-status", help="Current static abdication posture.")
def abdication_status() -> None:
    _run("abdication-status")


@click.command(name="abdication-schedule", help="Verify abdication schedule milestone integrity.")
def abdication_schedule() -> None:
    _run("abdication-schedule")


__all__ = ["abdication_schedule", "abdication_status", "parse_abdication_schedule"]

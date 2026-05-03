"""Small subprocess helpers shared by operator services."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

from xion_ops.exceptions import CommandFailed
from xion_ops.types import CommandResult


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    timeout: int | None = None,
    check: bool = True,
) -> CommandResult:
    """Run a command and return captured output.

    External tools stay behind service boundaries. Keeping this helper small
    makes command mocking straightforward in offline tests.
    """

    completed = subprocess.run(
        list(command),
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    result = CommandResult(
        command=tuple(command),
        returncode=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )
    if check and completed.returncode != 0:
        rendered = " ".join(command)
        raise CommandFailed(f"{rendered} failed with exit {completed.returncode}: {completed.stderr.strip()}")
    return result


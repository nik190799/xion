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
    stdin: str | None = None,
) -> CommandResult:
    """Run a command and return captured output.

    External tools stay behind service boundaries. Keeping this helper small
    makes command mocking straightforward in offline tests.

    When ``stdin`` is set it is fed to the process as UTF-8 (used for Typer CLI
    prompts that lack a ``--yes`` flag, such as upstream ``chutes`` 0.6.x).
    """

    cwd_str = str(cwd) if cwd else None
    if stdin is not None:
        completed = subprocess.run(
            list(command),
            cwd=cwd_str,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
            input=stdin,
        )
    else:
        completed = subprocess.run(
            list(command),
            cwd=cwd_str,
            text=True,
            encoding="utf-8",
            errors="replace",
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


"""`xion-verify soul-prompt` — Confirm genesis/SOUL_PROMPT.md matches the pinned hash.

Finding #2 verifier: asserts the file exists, matches PINNED_SOUL_PROMPT_SHA256,
and declares the Covenant Block.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

# Late import to avoid pulling orchestrator deps into the top level
# of xion-verify, but we need the constant.
def _get_pinned_hash() -> str:
    try:
        from orchestrator.cognition.soul_prompt import PINNED_SOUL_PROMPT_SHA256
        return PINNED_SOUL_PROMPT_SHA256
    except ImportError:
        # Fallback if orchestrator is not installed (e.g. auditor mode)
        return "0691f4d58b5b97f28e9694b1fa00b4941c412b2afd981976ccd7b1616a54803a"


@click.command(
    name="soul-prompt",
    help="Verify genesis/SOUL_PROMPT.md matches its pinned hash and declares the Covenant Block.",
)
def soul_prompt() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"soul-prompt: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    prompt_file = repo_root / "genesis" / "SOUL_PROMPT.md"
    if not prompt_file.is_file():
        click.echo("soul-prompt: FAIL: genesis/SOUL_PROMPT.md not found.", err=True)
        sys.exit(FAIL)
        
    actual_hash = sha256_file(prompt_file)
    expected_hash = _get_pinned_hash()
    
    if actual_hash != expected_hash:
        click.echo(
            f"soul-prompt: FAIL: genesis/SOUL_PROMPT.md hash mismatch\n"
            f"  expected: {expected_hash}\n"
            f"  actual:   {actual_hash}",
            err=True,
        )
        sys.exit(FAIL)
        
    content = prompt_file.read_text(encoding="utf-8")
    if "## Covenant Block" not in content:
        click.echo("soul-prompt: FAIL: genesis/SOUL_PROMPT.md does not declare the Covenant Block.", err=True)
        sys.exit(FAIL)
    
    click.echo("soul-prompt: OK (SOUL_PROMPT.md sha256 matches pin and declares Covenant Block)")
    sys.exit(OK)

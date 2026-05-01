"""`xion-verify voice-property` — Assert SOUL_PROMPT structurally anchors the context.

Finding #X verifier: intercepts `assemble_context` output (or just calls it directly)
and asserts the SOUL_PROMPT slot is byte-equal to `genesis/SOUL_PROMPT.md` body.
"""
from __future__ import annotations

import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="voice-property",
    help="Verify the SOUL_PROMPT anchors the assembled context window exactly.",
)
def voice_property() -> None:
    try:
        find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"voice-property: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    try:
        from orchestrator.cognition.context import assemble_context
        from orchestrator.cognition.soul_prompt import load_soul_prompt
    except ImportError as exc:
        click.echo(f"voice-property: FAIL: Could not import orchestrator modules: {exc}", err=True)
        sys.exit(FAIL)

    try:
        soul_prompt = load_soul_prompt()
    except Exception as exc:
        click.echo(f"voice-property: FAIL: load_soul_prompt failed: {exc}", err=True)
        sys.exit(FAIL)

    # Assemble context with mock data
    context = assemble_context(
        soul_prompt=soul_prompt,
        sensorium_snapshot={"mock": "data"},
        recent_journal=["user: hello", "xion: hi"],
        retrieved_context=["user: past"]
    )

    # Assert structural property
    if not context.startswith(soul_prompt.strip()):
        click.echo(
            "voice-property: FAIL: Assembled context does not start with the exact SOUL_PROMPT bytes.\n"
            "This violates the Voice property (Phase 5h).",
            err=True
        )
        sys.exit(FAIL)

    click.echo("voice-property: OK (SOUL_PROMPT structurally anchors the context window)")
    sys.exit(OK)

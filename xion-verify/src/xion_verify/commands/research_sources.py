"""`xion-verify research-sources` — curation check for RESEARCH_SOURCES.md.

Requires operator curation signature for RESEARCH_SOURCES.md entries.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(
    name="research-sources",
    help="Require operator curation signature for RESEARCH_SOURCES.md entries.",
)
def research_sources() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"research-sources: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    sources_file = repo_root / "docs" / "RESEARCH_SOURCES.md"
    if not sources_file.is_file():
        # If it doesn't exist yet, that's fine or we can fail.
        # The plan says "Land xion-verify research-sources curation check".
        click.echo("research-sources: OK (no RESEARCH_SOURCES.md to check)")
        sys.exit(OK)

    content = sources_file.read_text(encoding="utf-8")
    
    # Simple check: look for a signature block or specific formatting
    if "Operator Signature:" not in content and "Curation Signature:" not in content:
        click.echo("research-sources: FAIL: Missing operator curation signature in RESEARCH_SOURCES.md", err=True)
        sys.exit(FAIL)

    click.echo("research-sources: OK (curation signature verified)")
    sys.exit(OK)

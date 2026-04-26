"""`xion-verify covenant-addenda` — verify refusal/refund addenda are present."""

from __future__ import annotations

import hashlib
import re
import sys

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


@click.command(name="covenant-addenda", help="Verify Covenant addenda are present and hash-pinned.")
def covenant_addenda() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"covenant-addenda: FAIL: {exc}", err=True)
        sys.exit(FAIL)
    covenant_path = repo_root / "genesis" / "COVENANT.md"
    artifact_path = repo_root / "genesis" / "GENESIS_ARTIFACT.md"
    covenant = covenant_path.read_text(encoding="utf-8")
    artifact = artifact_path.read_text(encoding="utf-8")
    required = (
        "### Covenant Addendum — Refusal is Free",
        "### Covenant Addendum — Crisis Resource Surfacing",
    )
    for marker in required:
        if marker not in covenant:
            click.echo(f"covenant-addenda: FAIL: missing {marker}", err=True)
            sys.exit(FAIL)
    digest = hashlib.sha256(covenant_path.read_bytes()).hexdigest()
    match = re.search(r"COVENANT\.md\s+sha256:\s+([0-9a-f]{64})", artifact)
    if match is None or match.group(1) != digest:
        click.echo("covenant-addenda: FAIL: COVENANT.md hash is not pinned in GENESIS_ARTIFACT.md", err=True)
        sys.exit(FAIL)
    click.echo("covenant-addenda: OK (Refusal-is-Free and Crisis Resource Surfacing are present and pinned)")
    sys.exit(OK)


__all__ = ["covenant_addenda"]

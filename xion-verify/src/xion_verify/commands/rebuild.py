"""`xion-verify rebuild` — reproducible Docker build verifier.

Clones the repository at the currently checked-out SHA into a temporary directory,
runs `docker build` using the pinned base image, computes the image digest, and
compares it to `genesis/RELAY_IMAGE_DIGEST.txt`.

Important finding: the export extracts into ``temp_dir/xion-os`` (not ``temp_dir``).
Ad-hoc ``docker build`` from a different context path can produce a different image
ID with BuildKit; use the same layout as this command when pinning or publishing.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def _get_current_sha(repo_root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Failed to get current git SHA")
    return result.stdout.strip()


@click.command(
    name="rebuild",
    help="Verify reproducible Docker build against genesis/RELAY_IMAGE_DIGEST.txt.",
)
def rebuild() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"rebuild: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    digest_file = repo_root / "genesis" / "RELAY_IMAGE_DIGEST.txt"
    if not digest_file.is_file():
        click.echo("rebuild: NOT_YET_SEALED — genesis/RELAY_IMAGE_DIGEST.txt not found")
        sys.exit(NOT_YET_SEALED)

    expected_digest = digest_file.read_text(encoding="utf-8").strip()
    if not expected_digest:
        click.echo("rebuild: FAIL: genesis/RELAY_IMAGE_DIGEST.txt is empty", err=True)
        sys.exit(FAIL)

    try:
        sha = _get_current_sha(repo_root)
    except RuntimeError as e:
        click.echo(f"rebuild: FAIL: {e}", err=True)
        sys.exit(FAIL)

    click.echo(f"rebuild: Exporting {sha} to temp directory...")

    with tempfile.TemporaryDirectory() as temp_dir:
        clone_dir = Path(temp_dir) / "xion-os"
        clone_dir.mkdir()

        # Export the committed state
        res = subprocess.run(
            f"git archive {sha} | tar -x -C {clone_dir}",
            cwd=str(repo_root),
            shell=True,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            click.echo(f"rebuild: FAIL: git archive failed: {res.stderr}", err=True)
            sys.exit(FAIL)

        # Run docker build
        click.echo("rebuild: Running docker build...")
        if shutil.which("docker") is None:
            click.echo("rebuild: NOT_YET_SEALED — docker executable not found on this host")
            sys.exit(NOT_YET_SEALED)
        res = subprocess.run(
            ["docker", "build", "--provenance=false", "-q", "."],
            cwd=str(clone_dir),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            click.echo(f"rebuild: FAIL: docker build failed: {res.stderr}", err=True)
            sys.exit(FAIL)

        actual_digest = res.stdout.strip()

        if actual_digest != expected_digest:
            click.echo(f"rebuild: FAIL: digest mismatch. Expected {expected_digest}, got {actual_digest}", err=True)
            sys.exit(FAIL)

    click.echo("rebuild: OK (reproducible build verified)")
    sys.exit(OK)

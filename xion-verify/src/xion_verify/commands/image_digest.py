"""`xion-verify image-digest` — Relay image digest pin."""

from __future__ import annotations

import re
import shlex
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_DIGEST_PATH = "genesis/RELAY_IMAGE_DIGEST.txt"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def read_relay_image_digest(repo_root: Path) -> tuple[int, str]:
    path = repo_root / _DIGEST_PATH
    if not path.is_file():
        return NOT_YET_SEALED, f"{_DIGEST_PATH} not found"
    digest = path.read_text(encoding="utf-8").strip()
    if not digest:
        return NOT_YET_SEALED, f"{_DIGEST_PATH} is empty"
    if not _DIGEST_RE.fullmatch(digest):
        return FAIL, f"{_DIGEST_PATH} must contain sha256:<64 hex chars>"
    if not (repo_root / "Dockerfile").is_file():
        return FAIL, "Dockerfile not found"
    return OK, digest


def build_local_image_digest(repo_root: Path, tag: str | None = None) -> tuple[int, str]:
    """Build the local Relay image and return Docker's image ID digest."""
    with tempfile.TemporaryDirectory() as temp_dir:
        iidfile = Path(temp_dir) / "relay-image.iid"
        args = ["docker", "build", "--provenance=false", "--iidfile", str(iidfile)]
        if tag:
            args.extend(["-t", tag])
        args.append(".")
        try:
            result = subprocess.run(
                args,
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            if sys.platform == "win32":
                return _build_local_image_digest_with_wsl(repo_root, tag=tag)
            return FAIL, "docker executable not found"
        if result.returncode != 0:
            details = (result.stderr or result.stdout).strip()
            return FAIL, f"docker build failed: {details}"
        digest = iidfile.read_text(encoding="utf-8").strip() if iidfile.is_file() else result.stdout.strip()
    if not _DIGEST_RE.fullmatch(digest):
        return FAIL, f"docker build produced non-sha256 image id: {digest!r}"
    return OK, digest


def _build_local_image_digest_with_wsl(repo_root: Path, tag: str | None = None) -> tuple[int, str]:
    wsl_repo_root = _windows_path_to_wsl(repo_root)
    iidfile = f"/tmp/xion-relay-{uuid.uuid4().hex}.iid"
    tag_arg = f" -t {shlex.quote(tag)}" if tag else ""
    script = (
        f"rm -f {shlex.quote(iidfile)} && "
        f"docker build --provenance=false --iidfile {shlex.quote(iidfile)}{tag_arg} . && "
        f"cat {shlex.quote(iidfile)}"
    )
    try:
        result = subprocess.run(
            ["wsl.exe", "--cd", wsl_repo_root, "--exec", "sh", "-lc", script],
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return FAIL, "docker executable not found and WSL fallback is unavailable"
    if result.returncode != 0:
        details = (result.stderr or result.stdout).strip()
        return FAIL, f"WSL docker build failed: {details}"
    digest = _last_digest_line(result.stdout)
    if digest is None:
        return FAIL, f"WSL docker build produced no sha256 image id: {result.stdout.strip()!r}"
    return OK, digest


def _windows_path_to_wsl(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        return resolved.as_posix()
    relative = resolved.relative_to(resolved.anchor).as_posix()
    return f"/mnt/{drive}/{relative}"


def _last_digest_line(text: str) -> str | None:
    for line in reversed(text.splitlines()):
        candidate = line.strip()
        if _DIGEST_RE.fullmatch(candidate):
            return candidate
    return None


@click.command(name="image-digest", help="Verify the pinned Relay Docker image digest.")
@click.option(
    "--check-local",
    is_flag=True,
    help="Build the local Docker image and compare its image ID against genesis/RELAY_IMAGE_DIGEST.txt.",
)
@click.option(
    "--tag",
    default=None,
    help="Optional Docker tag to apply during --check-local builds.",
)
def image_digest(check_local: bool, tag: str | None) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"image-digest: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    code, message = read_relay_image_digest(repo_root)
    if code == OK:
        if check_local:
            local_code, local_digest = build_local_image_digest(repo_root, tag=tag)
            if local_code != OK:
                click.echo(f"image-digest: FAIL: {local_digest}", err=True)
                sys.exit(local_code)
            if local_digest != message:
                click.echo(
                    f"image-digest: FAIL: digest mismatch. Expected {message}, got {local_digest}",
                    err=True,
                )
                sys.exit(FAIL)
            click.echo(f"image-digest: OK (local Docker build matches {message})")
        else:
            click.echo(f"image-digest: OK ({message})")
    elif code == NOT_YET_SEALED:
        click.echo(f"image-digest: NOT_YET_SEALED — {message}")
    else:
        click.echo(f"image-digest: FAIL: {message}", err=True)
    sys.exit(code)


__all__ = ["build_local_image_digest", "image_digest", "read_relay_image_digest"]

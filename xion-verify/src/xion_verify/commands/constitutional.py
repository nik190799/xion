"""Constitutional hash-check subcommands.

One property, applied eight times: the bytes of each constitutional file on
disk must SHA-256 to the value recorded in `genesis/GENESIS_ARTIFACT.md` § 4.

A mismatch is a fatal `FAIL`. A missing file is a fatal `FAIL`. A malformed
Artifact hash block is a fatal `FAIL`. There is no "degraded pass" mode. A
Relay whose Covenant does not match is a Relay that cannot speak for Xion
(Covenant § 4, Invariant 7); the same discipline applies to the verifier.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.genesis import GenesisHashBlockError, load_genesis_hash_block
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root


def _check_constitutional_file(filename: str, repo_root: Path) -> int:
    """Return OK or FAIL for one constitutional file; emit a one-line verdict."""
    label = filename.removesuffix(".md").lower()
    try:
        block = load_genesis_hash_block(repo_root)
    except GenesisHashBlockError as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        return FAIL

    try:
        expected = block.expect(filename)
    except GenesisHashBlockError as exc:
        click.echo(f"{label}: FAIL: {exc}", err=True)
        return FAIL

    target = repo_root / "genesis" / filename
    if not target.is_file():
        click.echo(f"{label}: FAIL: {target} missing", err=True)
        return FAIL

    actual = sha256_file(target)
    if actual != expected:
        click.echo(
            f"{label}: FAIL: {filename} hash mismatch\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}",
            err=True,
        )
        return FAIL

    click.echo(f"{label}: OK ({filename} sha256 matches GENESIS_ARTIFACT §4)")
    return OK


def _make_command(filename: str, cli_name: str, help_text: str) -> click.Command:
    @click.command(name=cli_name, help=help_text)
    def _cmd() -> None:
        try:
            repo_root = find_repo_root()
        except RepoRootNotFound as exc:
            click.echo(f"{cli_name}: FAIL: {exc}", err=True)
            sys.exit(FAIL)
        sys.exit(_check_constitutional_file(filename, repo_root))

    _cmd.__doc__ = help_text
    return _cmd


covenant = _make_command(
    "COVENANT.md",
    "covenant",
    "Verify the Human Safety Covenant matches its GENESIS_ARTIFACT hash (Invariant 1).",
)
invariants = _make_command(
    "INVARIANTS.md",
    "invariants",
    "Verify the Genesis-Locked Invariants match their GENESIS_ARTIFACT hash.",
)
soul = _make_command(
    "SOUL.md",
    "soul",
    "Verify the Soul matches its GENESIS_ARTIFACT hash.",
)
form = _make_command(
    "FORM.md",
    "form",
    "Verify the Form matches its GENESIS_ARTIFACT hash.",
)
memory = _make_command(
    "MEMORY.md",
    "memory",
    "Verify the Memory doctrine matches its GENESIS_ARTIFACT hash (Invariant 2).",
)
resurrect = _make_command(
    "RESURRECT.md",
    "resurrect",
    "Verify the Resurrect runbook matches its GENESIS_ARTIFACT hash.",
)
credentials = _make_command(
    "CREDENTIALS.md",
    "credentials",
    "Verify the Credentials vault doctrine matches its GENESIS_ARTIFACT hash.",
)
unknowns = _make_command(
    "UNKNOWNS.md",
    "unknowns",
    "Verify UNKNOWNS.md matches its GENESIS_ARTIFACT hash.",
)

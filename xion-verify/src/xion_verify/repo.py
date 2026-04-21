"""Locate the Xion repository root from an arbitrary working directory.

Heuristic: walk upward from the current directory until we find a directory
that contains both `genesis/GENESIS_ARTIFACT.md` and `docs/00-INDEX.md`. That
pair is a strong witness that we are at the root of a Xion workspace and not,
for example, inside `xion-verify/` or `contracts/`. If no such directory is
found, raise `RepoRootNotFound`; the CLI converts that to a user-legible error.

We intentionally do not key off `.git/` because a Xion verifier must also run
from a raw `.tar.gz` of the repo (the post-genesis audit case), and we do not
key off `pyproject.toml` because several Xion subprojects will eventually carry
their own.
"""

from __future__ import annotations

from pathlib import Path


class RepoRootNotFound(RuntimeError):
    """Raised when no Xion repository root is discoverable from CWD upward."""


_WITNESSES: tuple[str, ...] = (
    "genesis/GENESIS_ARTIFACT.md",
    "docs/00-INDEX.md",
)


def find_repo_root(start: Path | None = None) -> Path:
    """Return the absolute Path of the Xion repo root.

    Raises `RepoRootNotFound` if no ancestor directory contains the witness
    files. An explicit `start` is useful for tests.
    """
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if all((candidate / w).is_file() for w in _WITNESSES):
            return candidate
    raise RepoRootNotFound(
        f"No Xion repo root at or above {here}. "
        f"Expected witnesses: {list(_WITNESSES)}"
    )

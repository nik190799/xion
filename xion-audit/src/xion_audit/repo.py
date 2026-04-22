"""Find the Xion monorepo root (same witness pair as `xion_verify.repo`)."""

from __future__ import annotations

from pathlib import Path

_WITNESS = (
    "genesis/GENESIS_ARTIFACT.md",
    "docs/00-INDEX.md",
)


def find_repo_root_or_cwd(start: Path | None = None) -> Path:
    here = (start or Path.cwd()).resolve()
    for c in (here, *here.parents):
        if all((c / w).is_file() for w in _WITNESS):
            return c
    raise FileNotFoundError(
        f"no Xion repo root at or above {here} (expected witnesses: {list(_WITNESS)})"
    )


def repo_root_not_found() -> None:  # pragma: no cover
    return None

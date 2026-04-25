"""Shared upgrade-level classification helpers.

The per-PR gate (`scripts/level_discipline.py`), the 90-day retrospective
(`provisioning-roles`), and contributor-facing tooling all speak through the
same machine-readable sources: `docs/schemas/levels.yaml` and
`docs/schemas/roles.yaml`. This module is the verifier-side helper for commands
that need to explain those sources without mutating them.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

_LEVELS_PATH = "docs/schemas/levels.yaml"
_ROLES_PATH = "docs/schemas/roles.yaml"


@dataclass(frozen=True)
class LevelSchemas:
    levels: dict[str, Any]
    roles: dict[str, Any]


@dataclass(frozen=True)
class PathClassification:
    path: str
    level_id: int | None
    level_name: str | None


def load_level_schemas(repo_root: Path) -> LevelSchemas | None:
    """Load `levels.yaml` and `roles.yaml`, returning None if absent/invalid."""
    levels_path = repo_root / _LEVELS_PATH
    roles_path = repo_root / _ROLES_PATH
    if not levels_path.is_file() or not roles_path.is_file():
        return None
    levels = yaml.safe_load(levels_path.read_text(encoding="utf-8"))
    roles = yaml.safe_load(roles_path.read_text(encoding="utf-8"))
    if not isinstance(levels, dict) or not isinstance(roles, dict):
        return None
    return LevelSchemas(levels=levels, roles=roles)


def level_by_id(levels: dict[str, Any], level_id: int) -> dict[str, Any] | None:
    """Return the level mapping for `level_id`, if present."""
    for level in levels.get("levels", []):
        try:
            if int(level["id"]) == level_id:
                return level
        except (KeyError, TypeError, ValueError):
            continue
    return None


def classify_path(path: str, levels: dict[str, Any]) -> int | None:
    """Return the upgrade level whose artifact globs match `path`.

    Unmapped paths are intentionally left as None so callers can either fail a
    mixed-level change or classify an all-unmapped change as Level 12 / Meta,
    matching the per-PR gate's existing discipline.
    """
    normalized = path.replace("\\", "/").strip()
    posix = PurePosixPath(normalized)
    for level in levels.get("levels", []):
        for pattern in level.get("artifacts") or []:
            if not isinstance(pattern, str) or not pattern:
                continue
            if "*" not in pattern and "?" not in pattern and "[" not in pattern:
                if normalized == pattern or normalized.startswith(pattern.rstrip("/") + "/"):
                    return int(level["id"])
                continue
            if posix.match(pattern):
                return int(level["id"])
    return None


def classify_paths(paths: list[str] | tuple[str, ...], levels: dict[str, Any]) -> list[PathClassification]:
    """Classify a path sequence with level names included for display."""
    out: list[PathClassification] = []
    for raw_path in paths:
        normalized = raw_path.replace("\\", "/").strip()
        level_id = classify_path(normalized, levels)
        level_name = None
        if level_id is not None:
            level = level_by_id(levels, level_id)
            if level is not None:
                level_name = str(level.get("name", f"Level {level_id}"))
        out.append(PathClassification(path=normalized, level_id=level_id, level_name=level_name))
    return out


def resolved_level_id(classifications: list[PathClassification]) -> int | None:
    """Return the single resolved level, or None if none/ambiguous.

    All-unmapped path sets are treated as Level 12 by the caller. Mixed mapped
    levels, or mapped + unmapped, are ambiguous and return None.
    """
    mapped = {c.level_id for c in classifications if c.level_id is not None}
    has_unmapped = any(c.level_id is None for c in classifications)
    if not mapped and classifications:
        return 12
    if len(mapped) == 1 and not has_unmapped:
        return next(iter(mapped))
    return None


def resolve_authorized_actors(level_id: int, levels: dict[str, Any], roles: dict[str, Any]) -> set[str]:
    """Return actor IDs authorized to initiate proposals for `level_id`."""
    level = level_by_id(levels, level_id)
    if level is None:
        return set()
    proposer = level.get("proposer")
    if not proposer:
        return set()
    bucket = roles.get("level_proposer_resolution", {}).get(proposer, {})
    return set(bucket.get("actors", []))

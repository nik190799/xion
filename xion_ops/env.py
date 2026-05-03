"""Small stdlib `.env` loader for xion-ops.

The operator CLI owns deployment orchestration, so it needs to see repo-local
environment values without requiring a separate shell export step. Existing
process environment variables always win.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_repo_env(repo_root: Path | str = ".") -> None:
    """Load KEY=VALUE pairs from `.env` without overwriting existing env vars."""

    env_path = Path(repo_root) / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = _unquote(value.strip())


def upsert_repo_env(repo_root: Path | str, values: dict[str, str], *, preserve_existing: bool = True) -> None:
    """Insert or update non-secret `.env` values atomically."""

    env_path = Path(repo_root) / ".env"
    existing = env_path.read_text(encoding="utf-8").splitlines() if env_path.is_file() else []
    seen: set[str] = set()
    output: list[str] = []
    for line in existing:
        if "=" not in line or line.lstrip().startswith("#"):
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in values:
            seen.add(key)
            if preserve_existing and line.split("=", 1)[1].strip():
                output.append(line)
            else:
                output.append(f"{key}={values[key]}")
        else:
            output.append(line)
    for key, value in values.items():
        if key not in seen:
            output.append(f"{key}={value}")
    env_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    load_repo_env(repo_root)


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value

"""`xion-verify schemas` — YAML schemas ↔ doctrine cross-check (strict).

Property promised. For every `*.yaml` file under `docs/schemas/`:

1. The file parses as valid YAML.
2. The top-level object has every field in `_REQUIRED_META`.
3. `status` is one of `{canonical, underspecified}`.
4. `source_doctrine` resolves to a repo-relative file that exists on disk.
5. The SHA-256 of that resolved file equals the value in `source_sha256` —
   byte-exact, strict. A mismatch is a fatal `FAIL` (see
   `docs/schemas/README.md` §"How is it verified?" for the rationale vs
   advisory soft-warnings).
6. If `status == underspecified`, a `defer_to` string field is present naming
   the roadmap phase that will promote the schema to `canonical`.

Directory missing → `NOT_YET_SEALED` (the folder did not exist pre-Phase 1b
and this exit code is the same honest answer any other unlanded artifact
returns).

Algorithm choice note (Invariant 14). SHA-256 is named only in
`xion_verify.hashing`; this module is algorithm-agnostic. A future crypto
migration that replaces SHA-256 adds a sibling hash in one place and every
call site here is unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click
import yaml

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.hashing import sha256_file
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SCHEMAS_DIRNAME = "docs/schemas"
_REQUIRED_META: tuple[str, ...] = (
    "schema_version",
    "source_doctrine",
    "source_sha256",
    "status",
)
_ALLOWED_STATUSES: frozenset[str] = frozenset({"canonical", "underspecified"})


def _fail(label: str, message: str) -> tuple[int, str]:
    return FAIL, f"{label}: FAIL: {message}"


def _check_one_schema(path: Path, repo_root: Path) -> tuple[int, str]:
    label = f"schemas[{path.relative_to(repo_root).as_posix()}]"

    try:
        raw = path.read_bytes()
    except OSError as exc:
        return _fail(label, f"cannot read: {exc}")

    try:
        data: Any = yaml.safe_load(raw.decode("utf-8"))
    except yaml.YAMLError as exc:
        return _fail(label, f"invalid YAML: {exc}")
    except UnicodeDecodeError as exc:
        return _fail(label, f"not valid UTF-8: {exc}")

    if not isinstance(data, dict):
        return _fail(label, "top-level YAML value must be a mapping")

    missing = [f for f in _REQUIRED_META if f not in data]
    if missing:
        return _fail(label, f"missing required meta fields: {', '.join(missing)}")

    status = data["status"]
    if status not in _ALLOWED_STATUSES:
        return _fail(
            label,
            f"status must be one of {sorted(_ALLOWED_STATUSES)}; got {status!r}",
        )

    if status == "underspecified" and "defer_to" not in data:
        return _fail(
            label,
            "status=underspecified requires a 'defer_to' field naming the roadmap phase",
        )

    source_rel = data["source_doctrine"]
    if not isinstance(source_rel, str) or not source_rel:
        return _fail(label, "source_doctrine must be a non-empty string")

    source_path = (repo_root / source_rel).resolve()
    try:
        source_path.relative_to(repo_root.resolve())
    except ValueError:
        return _fail(label, f"source_doctrine escapes repo root: {source_rel}")

    if not source_path.is_file():
        return _fail(label, f"source_doctrine does not exist: {source_rel}")

    expected_hash = data["source_sha256"]
    if not isinstance(expected_hash, str) or len(expected_hash) != 64:
        return _fail(label, "source_sha256 must be a 64-char hex SHA-256 string")

    actual_hash = sha256_file(source_path)
    if actual_hash != expected_hash:
        return _fail(
            label,
            (
                f"source_sha256 mismatch for {source_rel}\n"
                f"  expected: {expected_hash}\n"
                f"  actual:   {actual_hash}\n"
                f"  fix: rehash {source_rel} and update source_sha256 in the same commit"
            ),
        )

    detail = "canonical" if status == "canonical" else f"underspecified (defer_to: {data['defer_to']})"
    return OK, f"{label}: OK ({detail})"


@click.command(name="schemas")
def schemas() -> None:
    """Verify every docs/schemas/*.yaml byte-matches its doctrine source.

    Exit codes:
      0 OK              every schema parses, has required meta, and its
                        source_sha256 matches the current bytes of the
                        doctrine file it mirrors.
      1 FAIL            at least one schema failed a check.
      2 NOT_YET_SEALED  docs/schemas/ directory does not exist.
    """
    try:
        repo_root = find_repo_root(Path.cwd())
    except RepoRootNotFound as exc:
        click.echo(f"schemas: FAIL: {exc}", err=True)
        raise SystemExit(FAIL) from None

    schemas_dir = repo_root / _SCHEMAS_DIRNAME
    if not schemas_dir.is_dir():
        click.echo(
            f"schemas: NOT_YET_SEALED — {_SCHEMAS_DIRNAME}/ does not exist. "
            "(see DEVELOPMENT_ROADMAP.md Phase 1b)"
        )
        raise SystemExit(NOT_YET_SEALED)

    yaml_files = sorted(schemas_dir.glob("*.yaml"))
    if not yaml_files:
        click.echo(
            f"schemas: NOT_YET_SEALED — {_SCHEMAS_DIRNAME}/ has no *.yaml files yet. "
            "(see DEVELOPMENT_ROADMAP.md Phase 1b)"
        )
        raise SystemExit(NOT_YET_SEALED)

    worst = OK
    for yf in yaml_files:
        code, message = _check_one_schema(yf, repo_root)
        if code == OK:
            click.echo(message)
        else:
            click.echo(message, err=True)
            worst = max(worst, code)

    if worst == OK:
        click.echo(f"schemas: OK ({len(yaml_files)} schema file(s) verified against doctrine)")

    raise SystemExit(worst)

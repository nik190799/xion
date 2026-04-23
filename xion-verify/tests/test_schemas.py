"""Tests for `xion-verify schemas` — strict YAML ↔ doctrine cross-check."""

from __future__ import annotations

import contextlib
import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from xion_verify.commands.schemas import schemas
from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK


@contextlib.contextmanager
def _chdir(path: Path) -> Iterator[None]:
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _write_schema_with_doctrine(
    repo: Path,
    *,
    doctrine_rel: str,
    doctrine_body: bytes,
    schema_filename: str,
    override_meta: dict | None = None,
) -> tuple[Path, Path]:
    """Materialize a doctrine file and a schema YAML pointing at it."""
    doctrine_path = repo / doctrine_rel
    doctrine_path.parent.mkdir(parents=True, exist_ok=True)
    doctrine_path.write_bytes(doctrine_body)

    schemas_dir = repo / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    schema_path = schemas_dir / schema_filename

    meta = {
        "schema_version": 1,
        "source_doctrine": doctrine_rel,
        "source_sha256": hashlib.sha256(doctrine_body).hexdigest(),
        "status": "canonical",
    }
    if override_meta:
        meta.update(override_meta)
    schema_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    return doctrine_path, schema_path


def _invoke(repo: Path) -> tuple[int, str]:
    runner = CliRunner()
    with _chdir(repo):
        result = runner.invoke(schemas, [])
    return result.exit_code, result.output


# --- Real-repo smoke -----------------------------------------------------


def test_real_repo_schemas_pass(real_repo_root: Path) -> None:
    """The committed docs/schemas/*.yaml must verify against current doctrine."""
    code, output = _invoke(real_repo_root)
    assert code == OK, output
    assert "schemas: OK" in output


# --- NOT_YET_SEALED cases -----------------------------------------------


def test_missing_schemas_dir_returns_not_yet_sealed(synthetic_repo: Path) -> None:
    assert not (synthetic_repo / "docs" / "schemas").exists()
    code, output = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED, output
    assert "NOT_YET_SEALED" in output
    assert "docs/schemas/" in output


def test_empty_schemas_dir_returns_not_yet_sealed(synthetic_repo: Path) -> None:
    (synthetic_repo / "docs" / "schemas").mkdir(parents=True)
    code, output = _invoke(synthetic_repo)
    assert code == NOT_YET_SEALED, output
    assert "no *.yaml files" in output


# --- Happy path ---------------------------------------------------------


def test_valid_schema_passes(synthetic_repo: Path) -> None:
    _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
    )
    code, output = _invoke(synthetic_repo)
    assert code == OK, output
    assert "thing.yaml]: OK (canonical)" in output


def test_underspecified_status_requires_defer_to(synthetic_repo: Path) -> None:
    _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
        override_meta={"status": "underspecified"},
    )
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "defer_to" in output


def test_underspecified_with_defer_to_passes(synthetic_repo: Path) -> None:
    _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
        override_meta={"status": "underspecified", "defer_to": "Phase 9"},
    )
    code, output = _invoke(synthetic_repo)
    assert code == OK, output
    assert "underspecified (defer_to: Phase 9)" in output


# --- Failure cases ------------------------------------------------------


def test_tampered_doctrine_is_caught(synthetic_repo: Path) -> None:
    doctrine_path, _ = _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
    )
    doctrine_path.write_bytes(b"# Thing\nTAMPERED body\n")
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "source_sha256 mismatch" in output
    assert "rehash" in output


def test_tampered_schema_hash_is_caught(synthetic_repo: Path) -> None:
    _, schema_path = _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
    )
    content = yaml.safe_load(schema_path.read_text(encoding="utf-8"))
    content["source_sha256"] = "0" * 64
    schema_path.write_text(yaml.safe_dump(content, sort_keys=False), encoding="utf-8")
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "source_sha256 mismatch" in output


def test_missing_meta_fields_fail(synthetic_repo: Path) -> None:
    schemas_dir = synthetic_repo / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "bad.yaml").write_text("schema_version: 1\n", encoding="utf-8")
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "missing required meta fields" in output


def test_invalid_yaml_fails(synthetic_repo: Path) -> None:
    schemas_dir = synthetic_repo / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "broken.yaml").write_text(": : not valid :\n  - [\n", encoding="utf-8")
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "invalid YAML" in output


def test_missing_doctrine_file_fails(synthetic_repo: Path) -> None:
    schemas_dir = synthetic_repo / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "dangling.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "source_doctrine": "docs/never-created.md",
                "source_sha256": "0" * 64,
                "status": "canonical",
            }
        ),
        encoding="utf-8",
    )
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "does not exist" in output


def test_invalid_status_fails(synthetic_repo: Path) -> None:
    _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
        override_meta={"status": "draft"},
    )
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "status must be one of" in output


def test_path_escape_is_rejected(synthetic_repo: Path) -> None:
    schemas_dir = synthetic_repo / "docs" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)
    (schemas_dir / "escape.yaml").write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "source_doctrine": "../../../../../etc/passwd",
                "source_sha256": "0" * 64,
                "status": "canonical",
            }
        ),
        encoding="utf-8",
    )
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert ("escapes repo root" in output) or ("does not exist" in output)


def test_short_sha_is_rejected(synthetic_repo: Path) -> None:
    _write_schema_with_doctrine(
        synthetic_repo,
        doctrine_rel="docs/thing.md",
        doctrine_body=b"# Thing\nbody\n",
        schema_filename="thing.yaml",
        override_meta={"source_sha256": "abc123"},
    )
    code, output = _invoke(synthetic_repo)
    assert code == FAIL, output
    assert "64-char hex" in output


def test_schemas_command_is_registered(real_repo_root: Path) -> None:
    """The schemas subcommand must be in the CLI registry."""
    from xion_verify.commands import REGISTERED_COMMANDS

    assert "schemas" in REGISTERED_COMMANDS


# Silence unused-import warning when pytest is used to collect parametrized names.
_ = pytest

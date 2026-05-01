"""`xion-verify replay-corpus` — confirms manifest hash chain of the anonymized replay corpus.

Mirrors the shape of `xion-verify crisis-fidelity` or similar baseline_corpus checks.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root


def _verify_manifest(repo_root: Path) -> list[str]:
    errors = []
    manifest_path = repo_root / "xion-audit" / "replay_corpus" / "MANIFEST.jsonl"

    if not manifest_path.is_file():
        return ["xion-audit/replay_corpus/MANIFEST.jsonl not found"]

    try:
        lines = manifest_path.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        return [f"Failed to read MANIFEST.jsonl: {e}"]

    for line_idx, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"MANIFEST.jsonl line {line_idx + 1}: invalid JSON")
            continue

        path_str = entry.get("path")
        expected_sha = entry.get("sha256")

        if not path_str or not expected_sha:
            errors.append(f"MANIFEST.jsonl line {line_idx + 1}: missing path or sha256")
            continue

        item_path = repo_root / "xion-audit" / path_str
        if not item_path.is_file():
            errors.append(f"Missing corpus item: {path_str}")
            continue

        try:
            content = item_path.read_bytes()
        except Exception as e:
            errors.append(f"Failed to read {path_str}: {e}")
            continue

        actual_sha = hashlib.sha256(content).hexdigest()
        if actual_sha != expected_sha:
            errors.append(f"Hash mismatch for {path_str}: expected {expected_sha}, got {actual_sha}")

    return errors


@click.command(
    name="replay-corpus",
    help="Confirm manifest hash chain of the anonymized replay corpus.",
)
def replay_corpus() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"replay-corpus: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    errors = _verify_manifest(repo_root)
    if errors:
        for err in errors:
            click.echo(f"replay-corpus: FAIL: {err}", err=True)
        sys.exit(FAIL)

    click.echo("replay-corpus: OK (manifest hash chain verified)")
    sys.exit(OK)

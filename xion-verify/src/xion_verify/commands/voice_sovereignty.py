"""`xion-verify voice-sovereignty` — Invariant 18 (voice floor manifest)."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _fail(msg: str) -> None:
    click.echo(f"voice-sovereignty: FAIL: {msg}", err=True)
    raise SystemExit(FAIL)


def _sha256_file(repo: Path, rel: str) -> str:
    p = repo / rel
    if not p.is_file():
        _fail(f"sentinel missing: {p}")
    return hashlib.sha256(p.read_bytes()).hexdigest()


@click.command(name="voice-sovereignty")
def voice_sovereignty() -> None:
    """Verify the voice open-source floor manifest (Invariant 18, sentinel path)."""
    try:
        repo = find_repo_root(Path.cwd())
    except RepoRootNotFound as e:
        _fail(str(e))

    mpath = repo / "orchestrator" / "voice_router" / "voice_open_source_manifest.json"
    if not mpath.is_file():
        _fail(f"missing manifest: {mpath}")
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        _fail(f"cannot read manifest: {e}")

    rows = manifest.get("voice_open_source", [])
    if not isinstance(rows, list) or not rows:
        _fail("manifest has no 'voice_open_source' list or it is empty")

    floor = 0
    for i, ent in enumerate(rows):
        if not isinstance(ent, dict):
            _fail(f"voice_open_source[{i}] is not an object")
        if str(ent.get("category", "")) != "voice_open_source_self_hostable":
            continue
        floor += 1
        eid = str(ent.get("id", ""))
        if not eid:
            _fail(f"entry {i} missing id")
        if ent.get("format") != "sentinel":
            _fail(f"{eid}: only format=sentinel is implemented in voice-sovereignty v1")
        rel = ent.get("sentinel_path")
        if not isinstance(rel, str) or not rel:
            _fail(f"{eid}: missing sentinel_path")
        msha = str(ent.get("sha256", "")).lower()
        if not _RE_HEX64.match(msha):
            _fail(f"{eid}: sha256 must be 64 hex chars")
        got = _sha256_file(repo, rel)
        if got != msha:
            _fail(
                f"{eid}: sentinel sha256 mismatch: manifest {msha!r} != file {got!r} "
                f"for {rel}"
            )
        click.echo(f"  {eid}: sentinel OK ({rel})")

    if floor < 1:
        _fail(
            "no voice_open_source entry with category voice_open_source_self_hostable "
            "(Invariant 18 floor unsatisfied in manifest)"
        )

    click.echo(
        f"voice-sovereignty: OK  manifest {mpath} "
        f"({floor} floor pin(s) verified)"
    )
    raise SystemExit(OK)

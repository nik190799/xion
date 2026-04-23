"""`xion-verify inference-sovereignty` — Invariant 17 (live as of Phase 5 slice).

Asserts the repository checkout carries `orchestrator/inference_router/
open_weights_manifest.json` and that every `open_weights` entry in category
`open_weights_self_hostable` has a `sha256` that matches the on-disk
bytes of its referenced sentinel/weights file (paths are resolved
relative to the repository root). This is a *structural* floor check, not
a full model download: it proves the floor is wired, hash-pinned, and
independently recomputable by a Witness.
"""

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
    click.echo(f"inference-sovereignty: FAIL: {msg}", err=True)
    raise SystemExit(FAIL)


@click.command(name="inference-sovereignty")
def inference_sovereignty() -> None:
    """Verify the open-weights floor manifest and sentinel hashes (Invariant 17)."""
    try:
        repo = find_repo_root(Path.cwd())
    except RepoRootNotFound as e:
        _fail(str(e))

    mpath = repo / "orchestrator" / "inference_router" / "open_weights_manifest.json"
    if not mpath.is_file():
        _fail(f"missing manifest: {mpath}")
    try:
        manifest = json.loads(mpath.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        _fail(f"cannot read manifest: {e}")

    ows = manifest.get("open_weights", [])
    if not isinstance(ows, list) or not ows:
        _fail("manifest has no 'open_weights' list or it is empty")

    floor = 0
    for i, ent in enumerate(ows):
        if not isinstance(ent, dict):
            _fail(f"open_weights[{i}] is not an object")
        if str(ent.get("category", "")) != "open_weights_self_hostable":
            continue
        floor += 1
        eid = str(ent.get("id", ""))
        if not eid:
            _fail(f"open_weights entry {i} missing id")
        sha = str(ent.get("sha256", "")).lower()
        if not _RE_HEX64.match(sha):
            _fail(f"{eid}: sha256 is not 64 hex chars")
        if ent.get("format") == "sentinel" and "sentinel_path" in ent:
            rel = ent["sentinel_path"]
        elif "sentinel_path" in ent:
            rel = ent["sentinel_path"]
        else:
            _fail(f"{eid}: need sentinel_path or resolvable path for floor check")
        wpath = repo / str(rel)
        if not wpath.is_file():
            _fail(f"{eid}: weights/sentinel file missing: {wpath}")
        b = wpath.read_bytes()
        got = hashlib.sha256(b).hexdigest()
        if got != sha:
            _fail(
                f"{eid}: sha256 mismatch: manifest {sha!r} != file {wpath} {got!r}. "
                f"Re-pin or restore bytes."
            )

    if floor < 1:
        _fail(
            "no open_weights entry with category open_weights_self_hostable "
            "(Invariant 17 floor unsatisfied in manifest)"
        )

    click.echo(
        f"inference-sovereignty: OK  manifest {mpath} "
        f"lists {len(ows)} open_weights entr{'ies' if len(ows) != 1 else 'y'} "
        f"({floor} floor-satisfying self-hostable pin(s) verified by hash)"
    )
    raise SystemExit(OK)

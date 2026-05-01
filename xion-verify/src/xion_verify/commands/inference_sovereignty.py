"""`xion-verify inference-sovereignty` — Invariant 17.

Verifies the open-weights floor manifest at
`orchestrator/inference_router/open_weights_manifest.json`. As of
Phase 5g-viii three pin formats are accepted, dispatched per-format:

  - ``sentinel``           : hash-pinned structural stand-in proving the
                             floor wiring. The bytes of the file at
                             ``sentinel_path`` must sha256 to the
                             manifest's ``sha256`` field.

  - ``provenance-record``  : hash-pinned operator declaration about the
                             runtime daemon (e.g. the Ollama floor
                             provider). Same byte-equality check as
                             ``sentinel``; the meaning of the file is
                             different (it documents what the runtime
                             trusts), but the verifier treatment is
                             identical.

  - ``model-blob``         : hash-pinned upstream model artifact (e.g. a
                             Hugging Face GGUF file). The local copy of
                             the artifact is located via the env var
                             named in ``model_blob_env_var``; absent
                             path resolves to ``NOT_YET_SEALED`` for
                             that entry only. Present + sha256-matching
                             -> ``OK``. Present + sha256-mismatching ->
                             ``FAIL``.  Hashing is chunked (4 MiB
                             windows) so a 5 GB GGUF does not blow the
                             verifier's memory budget.

Unknown ``format`` values are ``FAIL`` (not silently skipped). Adding a
new format is a verifier change, not a manifest-only change. The
accepted-format set lives at exactly one place in the codebase: the
``_DISPATCH`` table below.

Exit codes:
  - ``OK`` (0)              : every floor-satisfying entry verified.
  - ``FAIL`` (1)            : structural error or hash mismatch on at
                              least one entry.
  - ``NOT_YET_SEALED`` (2)  : every entry verified except one or more
                              ``model-blob`` entries whose local file
                              was absent. Other formats never resolve
                              to ``NOT_YET_SEALED`` (the bytes they pin
                              are committed to git).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_RE_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_HASH_CHUNK_BYTES = 4 * 1024 * 1024  # 4 MiB; bounded peak memory for multi-GB GGUFs.


def _fail(msg: str) -> None:
    click.echo(f"inference-sovereignty: FAIL: {msg}", err=True)
    raise SystemExit(FAIL)


def _sha256_committed_file(repo: Path, rel: str, eid: str) -> str:
    """Hash a small repo-committed file (sentinel / provenance-record).

    These files are assumed to fit comfortably in memory; we read whole.
    Failure to read is a structural error (the bytes are part of the
    repo state).
    """
    wpath = repo / rel
    if not wpath.is_file():
        _fail(f"{eid}: file missing on disk: {wpath}")
    return hashlib.sha256(wpath.read_bytes()).hexdigest()


def _sha256_file_chunked(path: Path) -> str:
    """Hash a possibly multi-GB file with bounded peak memory.

    Raises FileNotFoundError / OSError on absent / unreadable; the
    caller is expected to have already verified ``path.is_file()``.
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(_HASH_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Per-format dispatch
# ---------------------------------------------------------------------------
#
# Each ``_verify_<format>`` returns one of:
#   ("ok",              human-readable summary)
#   ("not_yet_sealed",  human-readable summary)
# or raises via _fail().


def _verify_sentinel(repo: Path, ent: dict, eid: str, manifest_sha: str) -> tuple[str, str]:
    rel = ent.get("sentinel_path")
    if not isinstance(rel, str) or not rel:
        _fail(f"{eid}: format=sentinel requires a 'sentinel_path' string field")
    got = _sha256_committed_file(repo, rel, eid)
    if got != manifest_sha:
        _fail(
            f"{eid}: sentinel sha256 mismatch: manifest {manifest_sha!r} != "
            f"file {repo / rel} {got!r}. Re-pin or restore bytes."
        )
    return ("ok", f"{eid}: sentinel OK ({rel})")


def _verify_provenance_record(
    repo: Path, ent: dict, eid: str, manifest_sha: str
) -> tuple[str, str]:
    rel = ent.get("sentinel_path")
    if not isinstance(rel, str) or not rel:
        _fail(
            f"{eid}: format=provenance-record requires a 'sentinel_path' "
            f"string field naming the operator declaration"
        )
    got = _sha256_committed_file(repo, rel, eid)
    if got != manifest_sha:
        _fail(
            f"{eid}: provenance-record sha256 mismatch: manifest {manifest_sha!r} "
            f"!= file {repo / rel} {got!r}. Re-pin or restore bytes."
        )
    return ("ok", f"{eid}: provenance-record OK ({rel})")


def _verify_model_blob(
    repo: Path, ent: dict, eid: str, manifest_sha: str
) -> tuple[str, str]:
    env_var = ent.get("model_blob_env_var")
    if not isinstance(env_var, str) or not env_var:
        _fail(
            f"{eid}: format=model-blob requires a 'model_blob_env_var' string "
            f"field naming the env var the operator sets to the local file path"
        )

    hints = ent.get("retrieval_hints")
    if not isinstance(hints, list) or not hints:
        _fail(
            f"{eid}: format=model-blob requires a non-empty 'retrieval_hints' "
            f"list so a Witness can re-obtain the bytes the manifest pins"
        )
    for i, hint in enumerate(hints):
        if not isinstance(hint, dict):
            _fail(f"{eid}: retrieval_hints[{i}] is not an object")
        hint_url = hint.get("url")
        hint_sha = hint.get("sha256")
        if not isinstance(hint_url, str) or not hint_url:
            _fail(f"{eid}: retrieval_hints[{i}] missing 'url' string")
        if not isinstance(hint_sha, str) or not _RE_HEX64.match(hint_sha.lower()):
            _fail(f"{eid}: retrieval_hints[{i}] sha256 is not 64 hex chars")
        if hint_sha.lower() != manifest_sha:
            _fail(
                f"{eid}: retrieval_hints[{i}] sha256 {hint_sha!r} disagrees with "
                f"entry sha256 {manifest_sha!r}; the hint must point at the same "
                f"bytes the manifest pins"
            )

    raw_path = os.environ.get(env_var)
    if not raw_path:
        return (
            "not_yet_sealed",
            f"{eid}: model-blob NOT_YET_SEALED ({env_var} unset; "
            f"see docs/13-OPERATIONS.md \u00a7 \"First-time GGUF setup\" "
            f"to obtain and verify the upstream artifact)",
        )
    p = Path(raw_path)
    if not p.is_file():
        return (
            "not_yet_sealed",
            f"{eid}: model-blob NOT_YET_SEALED ({env_var}={raw_path!r} does "
            f"not resolve to a regular file; see docs/13-OPERATIONS.md "
            f"\u00a7 \"First-time GGUF setup\")",
        )

    size_pin = ent.get("size_bytes")
    if isinstance(size_pin, int) and size_pin > 0:
        try:
            on_disk_size = p.stat().st_size
        except OSError as e:
            _fail(f"{eid}: cannot stat model-blob file at {p}: {e}")
        if on_disk_size != size_pin:
            _fail(
                f"{eid}: model-blob size mismatch: manifest pin {size_pin} bytes "
                f"!= on-disk {on_disk_size} bytes ({p}). The file at {env_var} "
                f"is not the artifact the manifest pins; do not trust this floor."
            )

    try:
        got = _sha256_file_chunked(p)
    except OSError as e:
        _fail(f"{eid}: cannot read model-blob file at {p}: {e}")
    if got != manifest_sha:
        _fail(
            f"{eid}: model-blob sha256 mismatch: manifest {manifest_sha!r} "
            f"!= file {p} {got!r}. Either the file is corrupted in transit "
            f"(re-download) or the manifest pin is stale (re-run the C0(b) "
            f"probe in docs/26-INFERENCE-POLICY.md and re-pin)."
        )
    return ("ok", f"{eid}: model-blob OK ({p})")


_DISPATCH: dict[str, Callable[[Path, dict, str, str], tuple[str, str]]] = {
    "sentinel": _verify_sentinel,
    "provenance-record": _verify_provenance_record,
    "model-blob": _verify_model_blob,
}


@click.command(name="inference-sovereignty")
def inference_sovereignty() -> None:
    """Verify the open-weights floor manifest (Invariant 17, per-format)."""
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
    ok_count = 0
    nys_count = 0
    summaries: list[str] = []

    for i, ent in enumerate(ows):
        if not isinstance(ent, dict):
            _fail(f"open_weights[{i}] is not an object")
        if str(ent.get("category", "")) != "open_weights_self_hostable":
            continue
        floor += 1
        eid = str(ent.get("id", ""))
        if not eid:
            _fail(f"open_weights entry {i} missing id")

        manifest_sha = str(ent.get("sha256", "")).lower()
        if not _RE_HEX64.match(manifest_sha):
            _fail(f"{eid}: sha256 is not 64 hex chars")

        fmt = ent.get("format")
        if not isinstance(fmt, str) or fmt not in _DISPATCH:
            _fail(
                f"{eid}: unknown or missing 'format' (got {fmt!r}); "
                f"accepted formats are {sorted(_DISPATCH)}. Adding a new "
                f"format is a verifier change, not a manifest-only change."
            )

        verdict, msg = _DISPATCH[fmt](repo, ent, eid, manifest_sha)
        summaries.append(msg)
        if verdict == "ok":
            ok_count += 1
        elif verdict == "not_yet_sealed":
            nys_count += 1
        else:  # pragma: no cover - dispatch handlers raise via _fail() otherwise.
            _fail(f"{eid}: internal: dispatch returned unknown verdict {verdict!r}")

    if floor < 1:
        _fail(
            "no open_weights entry with category open_weights_self_hostable "
            "(Invariant 17 floor unsatisfied in manifest)"
        )

    for s in summaries:
        click.echo(f"  {s}")

    if nys_count > 0:
        click.echo(
            f"inference-sovereignty: NOT_YET_SEALED  manifest {mpath} "
            f"lists {len(ows)} open_weights entr{'ies' if len(ows) != 1 else 'y'} "
            f"({floor} floor-satisfying pins; {ok_count} OK + {nys_count} "
            f"NOT_YET_SEALED). Floor is structurally coherent; "
            f"NOT_YET_SEALED entries are operator-side gaps the verifier "
            f"surfaces but does not treat as failures."
        )
        raise SystemExit(NOT_YET_SEALED)

    click.echo(
        f"inference-sovereignty: OK  manifest {mpath} "
        f"lists {len(ows)} open_weights entr{'ies' if len(ows) != 1 else 'y'} "
        f"({floor} floor-satisfying pins, all hash-verified)"
    )
    raise SystemExit(OK)

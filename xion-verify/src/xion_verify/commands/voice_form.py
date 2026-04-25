"""`xion-verify voice-form` — `genesis/VOICE_FORM.md` structural check (Phase 6.5)."""

from __future__ import annotations

import json
import re
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_JSON_FENCE = re.compile(r"```json\s*(\{[\s\S]*?\})\s*```", re.MULTILINE)


def _fail(msg: str) -> None:
    click.echo(f"voice-form: FAIL: {msg}", err=True)
    raise SystemExit(FAIL)


@click.command(name="voice-form")
def voice_form() -> None:
    """Assert genesis/VOICE_FORM.md exists and contains a v0+ prosody JSON block."""
    try:
        repo = find_repo_root(Path.cwd())
    except RepoRootNotFound as e:
        _fail(str(e))
    p = repo / "genesis" / "VOICE_FORM.md"
    if not p.is_file():
        _fail(f"missing {p}")
    raw = p.read_text(encoding="utf-8")
    if "VOICE_FORM" not in raw:
        _fail("VOICE_FORM.md must identify itself")
    m = _JSON_FENCE.search(raw)
    if not m:
        _fail("no ```json fenced block with prosody schema")
    try:
        obj = json.loads(m.group(1))
    except json.JSONDecodeError as e:
        _fail(f"prosody JSON invalid: {e}")
    for key in ("voice_version", "pace_hz", "energy", "veil"):
        if key not in obj:
            _fail(f"prosody JSON missing required key {key!r}")
    click.echo(
        "voice-form: OK  genesis/VOICE_FORM.md prosody "
        f"v{obj['voice_version']} structurally valid"
    )
    raise SystemExit(OK)

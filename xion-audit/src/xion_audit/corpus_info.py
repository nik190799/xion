"""`xion-audit corpus-info` — print manifest and per-file counts."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import click
import json

from xion_audit.repo import find_repo_root_or_cwd


@click.command("corpus-info")
@click.option(
    "--regen-manifest",
    is_flag=True,
    help="(optional) recompute sha256/line_count into MANIFEST.jsonl from items/*.jsonl (developer use).",
)
def corpus_info(regen_manifest: bool) -> None:
    try:
        repo = find_repo_root_or_cwd()
    except FileNotFoundError as e:
        click.echo(f"corpus-info: FAIL: {e}", err=True)
        raise SystemExit(1)

    aud = repo / "xion-audit" / "baseline_corpus"
    if regen_manifest:
        _regen_manifest(aud)
    mpath = aud / "MANIFEST.jsonl"
    if not mpath.is_file():
        click.echo(f"corpus-info: FAIL: no manifest {mpath}", err=True)
        raise SystemExit(1)
    n_items = 0
    by_prin: Counter[str] = Counter()
    for line in mpath.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o: dict[str, Any] = json.loads(line)
        fpath = repo / "xion-audit" / str(o["path"])
        n_items += int(o.get("line_count", 0))
        by_file_prin(fpath, by_prin)
    click.echo(
        f"corpus-info: OK  {mpath}  total_items~={n_items}  "
        f"principle histogram (from expected_principle_id): {dict(sorted(by_prin.items()))}"
    )
    raise SystemExit(0)


def by_file_prin(fpath: Path, ctr: Counter[str]) -> None:
    if not fpath.is_file():
        return
    for line in fpath.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        pid = o.get("expected_principle_id")
        k = "ok" if o.get("expected_decision") == "ok" else (pid or "<?>")
        ctr[k] += 1


def _regen_manifest(aud: Path) -> None:
    import hashlib

    items = aud / "items"
    lines_out: list[str] = []
    for p in sorted(items.glob("*.jsonl")):
        b = p.read_bytes()
        h = hashlib.sha256(b).hexdigest()
        nlines = sum(1 for l in p.read_text(encoding="utf-8").splitlines() if l.strip())
        rel = f"baseline_corpus/items/{p.name}"
        o = {
            "path": rel,
            "byte_length": len(b),
            "sha256": h,
            "line_count": nlines,
        }
        lines_out.append(json.dumps(o, sort_keys=True))
    (aud / "MANIFEST.jsonl").write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    click.echo(f"regen: wrote {aud / 'MANIFEST.jsonl'}")


__all__ = ["corpus_info", "by_file_prin", "find_repo_root_or_cwd"]

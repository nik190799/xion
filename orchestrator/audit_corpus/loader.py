"""Load the Phase 4e `xion-audit/baseline_corpus/` from a repository checkout.

Pure stdlib. No file writes. `repo_root` is the directory that contains
`xion-audit/baseline_corpus/MANIFEST.jsonl`.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal, Optional

_RE_REL_PATH = re.compile(r"^(?:(?:baseline_corpus/))?(items/[^/]+\.jsonl)$")

ExpectedDecision = Literal["ok", "refuse", "escalate"]
ExpectedSource = Literal["v1_rule", "v2_llm", "either", "neither"]


@dataclass(frozen=True, slots=True)
class BaselineItem:
    """One baseline corpus line (JSON object)."""

    item_id: str
    schema_version: int
    candidate: str
    expected_decision: ExpectedDecision
    expected_principle_id: str | None
    expected_source: ExpectedSource
    raw: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ManifestRow:
    path: str
    byte_length: int
    sha256: str
    line_count: int


def repo_corpus_path(repo_root: Path) -> Path:
    return repo_root / "xion-audit" / "baseline_corpus"


def load_manifest(manifest_path: Path) -> tuple[ManifestRow, ...]:
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {manifest_path}")
    rows: list[ManifestRow] = []
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        o = json.loads(line)
        rows.append(
            ManifestRow(
                path=str(o["path"]),
                byte_length=int(o["byte_length"]),
                sha256=str(o["sha256"]),
                line_count=int(o["line_count"]),
            )
        )
    return tuple(rows)


def load_manifest_bytes(manifest_path: Path) -> bytes:
    return manifest_path.read_bytes()


def verify_manifest_against_items(repo_root: Path) -> None:
    """Raises ValueError on hash mismatch, length mismatch, or path skew."""
    base = repo_corpus_path(repo_root)
    manifest = base / "MANIFEST.jsonl"
    for row in load_manifest(manifest):
        m = _RE_REL_PATH.match(row.path)
        if not m:
            raise ValueError(f"manifest path not under items/: {row.path!r}")
        rel = m.group(1)  # items/<file>.jsonl
        fpath = base / rel
        if not fpath.is_file():
            raise ValueError(f"manifest references missing file: {fpath}")
        b = fpath.read_bytes()
        if len(b) != row.byte_length:
            raise ValueError(
                f"{fpath}: byte_length mismatch manifest={row.byte_length} actual={len(b)}"
            )
        digest = hashlib.sha256(b).hexdigest()
        if digest != row.sha256:
            raise ValueError(
                f"{fpath}: sha256 mismatch manifest={row.sha256} actual={digest}"
            )
        lines = sum(1 for x in fpath.read_text(encoding="utf-8").splitlines() if x.strip())
        if lines != row.line_count:
            raise ValueError(
                f"{fpath}: line_count mismatch manifest={row.line_count} actual={lines}"
            )


def _parse_item_obj(o: dict[str, Any]) -> BaselineItem:
    eid = str(o["item_id"])
    if not eid:
        raise ValueError("item_id empty")
    return BaselineItem(
        item_id=eid,
        schema_version=int(o["schema_version"]),
        candidate=str(o["candidate"]),
        expected_decision=o["expected_decision"],  # type: ignore[assignment]
        expected_principle_id=o.get("expected_principle_id") if o.get("expected_principle_id") is not None else None,
        expected_source=o["expected_source"],  # type: ignore[assignment]
        raw=dict(o),
    )


def _iter_item_files(base: Path) -> Iterator[Path]:
    items = base / "items"
    if not items.is_dir():
        raise FileNotFoundError(f"corpus items directory missing: {items}")
    for p in sorted(items.glob("*.jsonl")):
        if p.is_file():
            yield p


def load_repo_corpus(
    repo_root: Path, *, check_manifest: bool = True, strict_schema: bool = True
) -> list[BaselineItem]:
    if check_manifest:
        verify_manifest_against_items(repo_root)
    base = repo_corpus_path(repo_root)
    out: list[BaselineItem] = []
    for fpath in _iter_item_files(base):
        for line in fpath.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            o = json.loads(line)
            it = _parse_item_obj(o)
            if strict_schema:
                _strict_validate(it, o)
            out.append(it)
    return out


def _strict_validate(it: BaselineItem, o: dict[str, Any]) -> None:
    if it.expected_decision not in ("ok", "refuse", "escalate"):
        raise ValueError(f"{it.item_id}: bad expected_decision")
    if it.expected_decision == "ok" and it.expected_principle_id is not None:
        raise ValueError(f"{it.item_id}: expected_principle_id must be null when decision ok")
    if it.expected_decision != "ok" and not it.expected_principle_id:
        raise ValueError(f"{it.item_id}: expected_principle_id required for refuse/escalate")
    if bool(o.get("retired")) is True:  # future field
        pass
    cf = o.get("content_floor")
    if cf not in ("safe", "shape_only"):
        raise ValueError(f"{it.item_id}: content_floor must be safe|shape_only")
    if cf == "shape_only" and it.expected_decision == "ok":
        raise ValueError(
            f"{it.item_id}: content_floor=shape_only cannot pair with expected ok "
            f"(per baseline_corpus README)"
        )


__all__ = [
    "BaselineItem",
    "ExpectedDecision",
    "ExpectedSource",
    "ManifestRow",
    "load_manifest",
    "load_manifest_bytes",
    "load_repo_corpus",
    "repo_corpus_path",
    "verify_manifest_against_items",
]

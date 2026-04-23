"""`xion-verify links` — scan every markdown file for broken cross-references.

Property promised. Every markdown link in the doctrine corpus either resolves
to a file that exists, or is a legitimate external URL, or is a named genesis-
placeholder (`ar://`, `<<TX>>`). No silent rot. This is the mechanical version
of what Phase 0 remediation did by hand: a nav link in `13-OPERATIONS.md` that
points at the glossary instead of `14-UPGRADE-PATHS.md` fails this check.

What we scan. All `*.md` under the repo root — but not inside `xion-verify/`,
`node_modules/`, `.git/`, or `.dist/`. The agent transcripts folder and the
terminals folder are outside the repo root, so they are never scanned.

What counts as a link. Markdown link syntax `[label](target)` and reference-
style `[label]: target`. We strip `#fragment` and query strings before checking
file existence.

What is excluded. `http://`, `https://`, `mailto:`, `ar://`, `ipfs://`, `tel:`,
and bracketed placeholders like `<<...>>`. These are implementation-layer or
genesis-ceremony targets the verifier is not responsible for.

Forward references. A link to a file that does not yet exist on disk is a
broken link *unless* the target is enumerated in `xion-verify/ALLOWED_FORWARD_REFS.txt`.
That file is the single, reviewable place where deferred doctrine targets live,
each with a phase commitment and a reason. See `KNOWN_WEAKNESSES.md::KW-DOCS-003`.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

import click

from xion_verify.exit_codes import FAIL, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_ALLOWLIST_FILENAME = "ALLOWED_FORWARD_REFS.txt"

_INLINE_LINK = re.compile(r"(?<!\!)\[(?P<label>[^\]\n]*)\]\((?P<target>[^)\s]+)(?:\s+\"[^\"]*\")?\)")
_REFERENCE_LINK = re.compile(r"^\s{0,3}\[(?P<label>[^\]\n]+)\]:\s+(?P<target>\S+)", re.MULTILINE)

_SCHEME_ALLOWLIST: tuple[str, ...] = (
    "http://",
    "https://",
    "mailto:",
    "ar://",
    "ipfs://",
    "tel:",
    "ssh://",
    "git://",
)

_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".dist",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        ".cursor",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "xion-verify",  # self-excluded; the verifier's own README links are checked from inside its test suite
        # Foundry dependency vendor directories. OpenZeppelin and forge-std
        # ship their own READMEs with broken internal links (e.g. audit-report
        # PDFs we intentionally pruned during Phase 3 setup) that we do not
        # police. We trust OZ's own audit ledger for its contents; we trust
        # our pinned version for its bytecode.
        "lib",
        "out",
        "cache",
        "broadcast",
    }
)


@dataclass(frozen=True)
class BrokenLink:
    source: Path
    line_number: int
    label: str
    target: str
    reason: str

    def format(self, repo_root: Path) -> str:
        rel = self.source.relative_to(repo_root).as_posix()
        return f"{rel}:{self.line_number}: [{self.label}]({self.target}) — {self.reason}"


def load_allowed_forward_refs(repo_root: Path) -> frozenset[str]:
    """Parse `xion-verify/ALLOWED_FORWARD_REFS.txt` into a set of POSIX paths.

    Blank lines and `#`-prefixed comments are ignored. Every non-empty line
    must have the shape `<target>,<phase>,<reason>` — any deviation is a hard
    error so that the allowlist can never be silently corrupted into a
    catch-all.
    """
    path = repo_root / "xion-verify" / _ALLOWLIST_FILENAME
    if not path.is_file():
        return frozenset()
    targets: set[str] = set()
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(",", 2)
        if len(parts) != 3 or not all(p.strip() for p in parts):
            raise ValueError(
                f"{path}:{lineno}: malformed allowlist entry (expected '<target>,<phase>,<reason>'): {raw!r}"
            )
        targets.add(parts[0].strip().rstrip("/"))
        targets.add(parts[0].strip())
    return frozenset(targets)


def scan_markdown_files(repo_root: Path) -> list[Path]:
    """Return every `*.md` file under `repo_root`, excluding _EXCLUDED_DIRS."""
    out: list[Path] = []
    for path in repo_root.rglob("*.md"):
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(repo_root).parts):
            continue
        out.append(path)
    return sorted(out)


def check_link(
    source: Path,
    target: str,
    repo_root: Path,
    allowed_forward_refs: frozenset[str],
) -> str | None:
    """Return None if the link is OK, else a human-legible reason."""
    stripped = target.strip()
    if not stripped:
        return "empty target"
    if stripped.startswith("#"):
        # Intra-document anchor; we do not validate anchors in v1 (Phase 1b).
        return None
    if stripped.startswith("<") and stripped.endswith(">"):
        # Genesis-ceremony placeholder like <<ARWEAVE_BUNDLE_TX>>.
        return None
    for scheme in _SCHEME_ALLOWLIST:
        if stripped.startswith(scheme):
            return None
    path_part = stripped.split("#", 1)[0].split("?", 1)[0]
    if not path_part:
        return None
    resolved = (source.parent / path_part).resolve()
    if resolved.exists():
        return None
    try:
        repo_relative = resolved.relative_to(repo_root).as_posix()
    except ValueError:
        return f"target does not exist: {resolved}"
    if repo_relative in allowed_forward_refs:
        return None
    if f"{repo_relative}/" in allowed_forward_refs:
        return None
    return f"target does not exist: {resolved}"


def find_broken_links(repo_root: Path) -> list[BrokenLink]:
    """Scan every non-excluded markdown file and return every broken link."""
    broken: list[BrokenLink] = []
    allowed = load_allowed_forward_refs(repo_root)
    for path in scan_markdown_files(repo_root):
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in _INLINE_LINK.finditer(line):
                reason = check_link(path, m.group("target"), repo_root, allowed)
                if reason is not None:
                    broken.append(
                        BrokenLink(
                            source=path,
                            line_number=lineno,
                            label=m.group("label"),
                            target=m.group("target"),
                            reason=reason,
                        )
                    )
        for m in _REFERENCE_LINK.finditer(text):
            pos = m.start()
            lineno = text.count("\n", 0, pos) + 1
            reason = check_link(path, m.group("target"), repo_root, allowed)
            if reason is not None:
                broken.append(
                    BrokenLink(
                        source=path,
                        line_number=lineno,
                        label=m.group("label"),
                        target=m.group("target"),
                        reason=reason,
                    )
                )
    return broken


@click.command(
    name="links",
    help="Scan every markdown file in the corpus for broken cross-references (closes KW-DOCS-001 mechanically).",
)
def links() -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"links: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    broken = find_broken_links(repo_root)
    if broken:
        for bl in broken:
            click.echo(f"links: FAIL: {bl.format(repo_root)}", err=True)
        click.echo(f"links: FAIL: {len(broken)} broken link(s) across the corpus", err=True)
        sys.exit(FAIL)

    scanned = len(scan_markdown_files(repo_root))
    click.echo(f"links: OK ({scanned} markdown file(s) scanned; zero broken cross-references)")
    sys.exit(OK)

"""Parser for the constitutional hash block in `genesis/GENESIS_ARTIFACT.md` § 4.

The hash block lives inside a triple-backticked code fence immediately after
the sentence in § 4 that introduces it. Each line has the shape:

    <FILENAME>  sha256: <lowercase-hex>

with arbitrary whitespace between the filename and the `sha256:` literal. We
parse exactly that shape and nothing else. If the Artifact is ever restructured,
this parser fails loud; silent reinterpretation of the hash block would be a
constitutional violation disguised as code hygiene.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_HASH_LINE = re.compile(
    r"^(?P<filename>[A-Z][A-Z0-9_]*\.md)\s+sha256:\s+(?P<hash>[0-9a-f]{64})\s*$"
)

# Files the verifier expects to find in the hash block. If the Artifact ever
# adds a new constitutional file, add it here in the same commit that updates
# GENESIS_ARTIFACT.md and its own subcommand — that coupling is intentional.
EXPECTED_CONSTITUTIONAL_FILES: tuple[str, ...] = (
    "COVENANT.md",
    "INVARIANTS.md",
    "SOUL.md",
    "FORM.md",
    "MEMORY.md",
    "RESURRECT.md",
    "CREDENTIALS.md",
    "UNKNOWNS.md",
)


class GenesisHashBlockError(RuntimeError):
    """Raised when the Genesis Artifact's hash block cannot be parsed."""


@dataclass(frozen=True)
class GenesisHashBlock:
    """The parsed contents of GENESIS_ARTIFACT.md § 4's hash fence."""

    hashes: dict[str, str]
    source_path: Path

    def expect(self, filename: str) -> str:
        """Return the hash for `filename`, or raise `GenesisHashBlockError`."""
        if filename not in self.hashes:
            raise GenesisHashBlockError(
                f"{self.source_path}: hash block does not contain an entry for {filename}"
            )
        return self.hashes[filename]


def load_genesis_hash_block(repo_root: Path) -> GenesisHashBlock:
    """Read and parse `genesis/GENESIS_ARTIFACT.md` § 4."""
    path = repo_root / "genesis" / "GENESIS_ARTIFACT.md"
    text = path.read_text(encoding="utf-8")
    hashes: dict[str, str] = {}
    in_fence = False
    fence_consumed = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_fence:
                in_fence = False
                fence_consumed = True
                break
            if _is_hash_fence_anchor(text, line) and not fence_consumed:
                in_fence = True
            continue
        if not in_fence:
            continue
        if not stripped:
            continue
        m = _HASH_LINE.match(stripped)
        if not m:
            raise GenesisHashBlockError(
                f"{path}: unparseable hash-block line: {stripped!r}. "
                f"Expected '<FILENAME>.md  sha256: <64-hex>'."
            )
        filename = m.group("filename")
        if filename in hashes:
            raise GenesisHashBlockError(
                f"{path}: duplicate hash-block entry for {filename}"
            )
        hashes[filename] = m.group("hash")
    if not hashes:
        raise GenesisHashBlockError(
            f"{path}: no parsable hash block found. "
            f"Expected a fenced code block in § 4 containing '<FILENAME>.md  sha256: ...'."
        )
    missing = [f for f in EXPECTED_CONSTITUTIONAL_FILES if f not in hashes]
    if missing:
        raise GenesisHashBlockError(
            f"{path}: hash block is missing expected constitutional entries: {missing}"
        )
    return GenesisHashBlock(hashes=hashes, source_path=path)


def _is_hash_fence_anchor(full_text: str, fence_line: str) -> bool:
    """Heuristic: only pick the first fence whose prior paragraph introduces it.

    The hash block is immediately preceded (within the paragraph above) by the
    phrase 'SHA-256' or 'pre-genesis documentation witness' in the current
    Artifact. If neither phrase appears anywhere before the fence, we refuse to
    treat it as the hash block and fail loud.
    """
    idx = full_text.find(fence_line)
    if idx == -1:
        return False
    preamble = full_text[:idx]
    return "SHA-256" in preamble or "pre-genesis documentation witness" in preamble

"""SHA-256 helpers with byte-exact semantics.

Every hash comparison in xion-verify must be byte-for-byte. We never normalize
line endings, trim whitespace, or re-encode. The SHA-256 of a file is the
SHA-256 of its exact bytes on disk. A file that disagrees with its recorded
hash by one CRLF is not the same file.

Algorithm choice note (Invariant 14 — Crypto-Agility Mandate). SHA-256 is the
implementation today. This module is the only place in the verifier that names
a hash family; future migrations will add sibling functions (e.g., `blake3_file`,
`sha3_file`) and a resolver that picks the active family from the runtime
crypto policy. The constitutional property "every committed file is verifiably
hashed" is what the verifier enforces; SHA-256 is how it enforces it today.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

_CHUNK_BYTES = 1 << 20


def sha256_file(path: Path) -> str:
    """Return the lowercase-hex SHA-256 of the file's exact bytes."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(_CHUNK_BYTES)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Return the lowercase-hex SHA-256 of the given bytes."""
    return hashlib.sha256(data).hexdigest()


def tree_hash(root: Path, patterns: tuple[str, ...], exclude: frozenset[Path] = frozenset()) -> str:
    """Deterministic hash of a file tree.

    Walks `root` for files matching any of `patterns` (Path.glob-style), sorted
    by POSIX relative path for determinism across operating systems, and emits
    a single SHA-256 over lines of the form:

        <relative-posix-path>\\n<file-sha256>\\n

    A file listed in `exclude` (absolute Path) is skipped. This is what
    `--self-test` hashes the verifier source with — the pin file is excluded
    because a file cannot contain the hash of itself.
    """
    lines: list[str] = []
    seen: set[Path] = set()
    for pattern in patterns:
        for candidate in sorted(root.glob(pattern)):
            if not candidate.is_file():
                continue
            if candidate.resolve() in exclude:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
    for candidate in sorted(seen, key=lambda p: p.relative_to(root).as_posix()):
        rel = candidate.relative_to(root).as_posix()
        lines.append(f"{rel}\n{sha256_file(candidate)}\n")
    return sha256_bytes("".join(lines).encode("utf-8"))

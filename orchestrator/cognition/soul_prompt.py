"""Phase 5g-i.1 Voice Layer: The Soul Prompt loader.

Doctrine anchor: docs/24-COGNITION.md § "The Phase 5g-i.1 voice layer".

Reads genesis/SOUL_PROMPT.md, verifies its SHA-256 against a pinned
constant, and returns the body for injection into the /chat handler's
system prompt slot.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

# The exact SHA-256 of genesis/SOUL_PROMPT.md.
# A mismatch means the file was edited without updating this pin.
# The `xion-verify soul-prompt` subcommand checks this offline.
PINNED_SOUL_PROMPT_SHA256 = "84bde58a5a29c14ead45829e357bdaa0abb4cd48663d1a39e28043540361faf4"

class SoulPromptHashMismatchError(Exception):
    """Raised when genesis/SOUL_PROMPT.md does not match the pinned hash."""


_cached_body: str | None = None
_cached_mtime: float = 0.0


def _find_repo_root() -> Path:
    """Locate ``genesis/SOUL_PROMPT.md`` for hash verification.

    Order: explicit ``XION_REPO_ROOT``, then walk from ``Path.cwd()`` (so
    Docker ``WORKDIR=/app`` layouts with only ``genesis/SOUL_PROMPT.md``
    copied in work), then walk from this file (editable installs / dev).
    """
    env_root = os.environ.get("XION_REPO_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root)
        if (candidate / "genesis" / "SOUL_PROMPT.md").is_file():
            return candidate

    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / "genesis" / "SOUL_PROMPT.md").is_file():
            return base

    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "genesis" / "SOUL_PROMPT.md").is_file():
            return current
        current = current.parent
    raise RuntimeError("Could not find repository root containing genesis/SOUL_PROMPT.md")


def load_soul_prompt() -> str:
    """Read and hash-verify genesis/SOUL_PROMPT.md.

    Returns the body of the prompt (the Covenant Block onward, with the
    topmost `# SOUL_PROMPT.md ...` header stripped).

    Caches the result in-memory keyed on the file's mtime so the
    orchestrator does not re-hash per request.
    """
    global _cached_body, _cached_mtime

    repo_root = _find_repo_root()
    path = repo_root / "genesis" / "SOUL_PROMPT.md"

    try:
        stat = os.stat(path)
    except FileNotFoundError:
        raise SoulPromptHashMismatchError(f"File not found: {path}") from None

    if _cached_body is not None and stat.st_mtime == _cached_mtime:
        return _cached_body

    with open(path, "rb") as f:
        raw = f.read()

    actual_hash = hashlib.sha256(raw).hexdigest()
    if actual_hash != PINNED_SOUL_PROMPT_SHA256:
        raise SoulPromptHashMismatchError(
            f"genesis/SOUL_PROMPT.md hash mismatch.\n"
            f"Expected: {PINNED_SOUL_PROMPT_SHA256}\n"
            f"Actual:   {actual_hash}"
        )

    text = raw.decode("utf-8")

    # Strip the topmost header and intro paragraph if present,
    # starting the prompt at the Covenant Block.
    lines = text.splitlines()
    start_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("## Covenant Block"):
            start_idx = i
            break

    body = "\n".join(lines[start_idx:])

    _cached_body = body
    _cached_mtime = stat.st_mtime
    return body

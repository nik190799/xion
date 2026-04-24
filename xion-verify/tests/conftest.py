"""Shared pytest fixtures for xion-verify."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def real_repo_root() -> Path:
    """The real Xion repo root this test suite lives inside."""
    return REPO_ROOT


@pytest.fixture
def synthetic_repo(tmp_path: Path) -> Path:
    """Build a minimal in-memory Xion repo with a valid GENESIS_ARTIFACT hash block.

    Tests that exercise the parser's happy path operate against this rather
    than the real repo so that a legitimate change to real doctrine does not
    require rewriting the test suite.
    """
    genesis = tmp_path / "genesis"
    docs = tmp_path / "docs"
    genesis.mkdir()
    docs.mkdir()

    constitutional_bodies: dict[str, bytes] = {
        "COVENANT.md": b"# Covenant\nSynthetic body.\n",
        "INVARIANTS.md": b"# Invariants\nSynthetic body.\n",
        "SOUL.md": b"# Soul\nSynthetic body.\n",
        "SOUL_PROMPT.md": b"## Covenant Block\nSynthetic body.\n",
        "FORM.md": b"# Form\nSynthetic body.\n",
        "MEMORY.md": b"# Memory\nSynthetic body.\n",
        "RESURRECT.md": b"# Resurrect\nSynthetic body.\n",
        "CREDENTIALS.md": b"# Credentials\nSynthetic body.\n",
        "UNKNOWNS.md": b"# Unknowns\nSynthetic body.\n",
    }
    hashes: dict[str, str] = {}
    for name, body in constitutional_bodies.items():
        (genesis / name).write_bytes(body)
        hashes[name] = hashlib.sha256(body).hexdigest()

    hash_lines = "\n".join(f"{name:<16}sha256: {h}" for name, h in hashes.items())
    artifact = (
        "# Genesis Artifact (synthetic)\n\n"
        "## 4. Constitutional hash witness\n\n"
        "SHA-256 hashes of the constitutional bundle as a pre-genesis documentation witness.\n\n"
        "```\n"
        f"{hash_lines}\n"
        "```\n"
    )
    (genesis / "GENESIS_ARTIFACT.md").write_bytes(artifact.encode("utf-8"))
    (docs / "00-INDEX.md").write_bytes(b"# Docs index\n")
    return tmp_path

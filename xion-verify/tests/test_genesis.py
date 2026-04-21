"""Tests for `xion_verify.genesis`.

Property under test: the Genesis Artifact parser accepts valid hash blocks,
rejects malformed lines loudly, and reports missing constitutional entries.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from xion_verify.genesis import (
    EXPECTED_CONSTITUTIONAL_FILES,
    GenesisHashBlockError,
    load_genesis_hash_block,
)


def test_parse_synthetic_happy_path(synthetic_repo: Path) -> None:
    block = load_genesis_hash_block(synthetic_repo)
    for name in EXPECTED_CONSTITUTIONAL_FILES:
        assert name in block.hashes
        assert len(block.expect(name)) == 64


def test_parser_rejects_unparseable_line(synthetic_repo: Path) -> None:
    artifact = synthetic_repo / "genesis" / "GENESIS_ARTIFACT.md"
    text = artifact.read_text(encoding="utf-8")
    corrupted = text.replace("COVENANT.md", "COVENANT.md NONHEX")
    artifact.write_text(corrupted, encoding="utf-8")
    with pytest.raises(GenesisHashBlockError):
        load_genesis_hash_block(synthetic_repo)


def test_parser_reports_missing_file(synthetic_repo: Path) -> None:
    artifact = synthetic_repo / "genesis" / "GENESIS_ARTIFACT.md"
    text = artifact.read_text(encoding="utf-8")
    pruned = "\n".join(
        line for line in text.splitlines() if not line.startswith("COVENANT.md")
    )
    artifact.write_text(pruned, encoding="utf-8")
    with pytest.raises(GenesisHashBlockError, match=r"COVENANT\.md"):
        load_genesis_hash_block(synthetic_repo)


def test_real_repo_parses_cleanly(real_repo_root: Path) -> None:
    """The real GENESIS_ARTIFACT § 4 must remain parseable."""
    block = load_genesis_hash_block(real_repo_root)
    for name in EXPECTED_CONSTITUTIONAL_FILES:
        assert name in block.hashes

"""Baseline corpus loader integrity."""

from __future__ import annotations

from pathlib import Path

import pytest

from orchestrator.audit_corpus import load_repo_corpus, verify_manifest_against_items


def test_verify_and_load_repo_corpus(repo_root: Path):
    verify_manifest_against_items(repo_root)
    items = load_repo_corpus(repo_root, check_manifest=True)
    assert len(items) >= 1
    assert all(i.item_id for i in items)


@pytest.fixture
def repo_root() -> Path:
    root = Path(__file__).resolve().parents[2]
    if not (root / "genesis" / "GENESIS_ARTIFACT.md").is_file():
        pytest.skip("not in a full xion-os checkout")
    return root

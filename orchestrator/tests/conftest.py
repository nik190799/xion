"""Shared pytest fixtures for orchestrator tests.

Keeps every test hermetic: each test writes to its own tmp_path ledger;
no test ever touches the repo-root SAFETY_LEDGER.jsonl.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    """A fresh ledger file path per test."""
    return tmp_path / "SAFETY_LEDGER.jsonl"

"""Shared pytest fixtures for orchestrator tests.

Keeps every test hermetic: each test writes to its own tmp_path ledger;
no test ever touches the repo-root SAFETY_LEDGER.jsonl or the repo-root
SENSORIUM_LEDGER.jsonl.
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def ledger_path(tmp_path: Path) -> Path:
    """A fresh SAFETY_LEDGER path per test."""
    return tmp_path / "SAFETY_LEDGER.jsonl"


@pytest.fixture
def sensorium_ledger_path(tmp_path: Path) -> Path:
    """A fresh SENSORIUM_LEDGER path per test (Phase 5d).

    Phase 5d's gate() — on the append_to_ledger=True distress path —
    writes a SENSORIUM distress row alongside the SAFETY escalation row.
    Tests that exercise that path MUST pass ``sensorium_ledger_path=``
    through, or gate() will fall back to the repo-root default and
    contaminate the real ledger.
    """
    return tmp_path / "SENSORIUM_LEDGER.jsonl"


@pytest.fixture(autouse=True)
def _no_repo_sensorium_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hermeticity safety net (Phase 5d).

    Any test that forgets to pass ``sensorium_ledger_path=`` through a
    distress-path gate() call would otherwise hit
    ``_default_sensorium_ledger_path()`` and write into the repo root.
    This autouse fixture redirects ``XION_SENSORIUM_LEDGER`` to the per-
    test tmp_path so a forgotten kwarg contaminates nothing. Tests that
    want the explicit-kwarg behaviour still assert against the returned
    path from the ``sensorium_ledger_path`` fixture.
    """
    monkeypatch.setenv(
        "XION_SENSORIUM_LEDGER",
        str(tmp_path / "_autouse_SENSORIUM_LEDGER.jsonl"),
    )

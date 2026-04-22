"""Shared pytest fixtures for orchestrator tests.

Keeps every test hermetic: each test writes to its own tmp_path ledger;
no test ever touches the repo-root SAFETY_LEDGER.jsonl or the repo-root
SENSORIUM_LEDGER.jsonl.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

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


@pytest.fixture
def app_factory(
    ledger_path: Path,
    sensorium_ledger_path: Path,
) -> Callable[..., Any]:
    """Build a fully-wired Phase 5f FastAPI app around a per-test Relay
    and hermetic SAFETY / SENSORIUM ledgers.

    Usage:
        def test_drive(app_factory):
            app = app_factory(tick_cadence_s=0.01)
            from fastapi.testclient import TestClient
            with TestClient(app) as client:
                r = client.get("/drive")
                assert r.status_code == 200

    Kwargs are forwarded to ``AppDeps``; the Relay is constructed with
    the per-test ``ledger_path`` and ``sensorium_ledger_path`` so no
    test can contaminate the repo-root ledgers. ``tick_cadence_s``
    defaults to 0.01 so tests do not wait on the Genesis Default (10s).

    Skips if the ``[api]`` optional extra is not installed.
    """

    def _factory(
        *,
        tick_cadence_s: float = 0.01,
        methodology_hash: str | None = None,
        **relay_kwargs: Any,
    ) -> Any:
        pytest.importorskip("fastapi")
        pytest.importorskip("pydantic")
        from orchestrator.api import AppDeps, create_app
        from orchestrator.relay import Relay

        relay = Relay(
            safety_ledger_path=ledger_path,
            sensorium_ledger_path=sensorium_ledger_path,
            **relay_kwargs,
        )
        deps = AppDeps(
            relay=relay,
            tick_cadence_s=tick_cadence_s,
            methodology_hash=methodology_hash,
            sensorium_ledger_path=sensorium_ledger_path,
        )
        app = create_app(deps)
        # Stash the Relay on app.state so tests can inspect/mutate it
        # without re-reading app.state.deps.relay every time.
        app.state.test_relay = relay
        return app

    return _factory

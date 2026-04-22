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
def _no_repo_ledger_leaks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hermeticity safety net (Phase 5d + 5g-i).

    Any test that forgets to pass an explicit ledger path would
    otherwise hit one of the ``_default_*_ledger_path()`` resolvers and
    write into the repo root. This autouse fixture redirects both the
    SENSORIUM and REQUEST ledger env vars to per-test tmp_path files
    so a forgotten kwarg contaminates nothing. (The SAFETY_LEDGER path
    is already hermetic because Relay requires an explicit
    ``safety_ledger_path`` — see ``app_factory``.)

    Phase 5g-i added ``POST /chat``, which makes every chat turn
    write TWO REQUEST_LEDGER rows (one per Arbiter call). Without this
    redirection, the Chat test suite would leak rows into the repo
    root every run.
    """
    monkeypatch.setenv(
        "XION_SENSORIUM_LEDGER",
        str(tmp_path / "_autouse_SENSORIUM_LEDGER.jsonl"),
    )
    monkeypatch.setenv(
        "XION_REQUEST_LEDGER",
        str(tmp_path / "_autouse_REQUEST_LEDGER.jsonl"),
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
        generative_provider: Any = None,
        floor_stub_id: str | None = "sentinel-llm-v0",
        no_floor: bool = False,
        policy_mode: str = "hosted_api_first",
        chat_deadline_s: float = 5.0,
        **relay_kwargs: Any,
    ) -> Any:
        """Build a hermetic FastAPI app for tests.

        Kwargs:
            generative_provider: Optional mock provider to register for
                turn serving. Tests typically pass a fake with a
                ``generate`` method. If ``floor_stub_id`` is also set,
                the floor stub is registered alongside so
                ``InferenceRouter.bootstrap()`` passes.
            floor_stub_id: Manifest id of the
                ``OpenWeightsFloorStub`` to register. Set to None to
                skip floor registration — combined with no
                generative_provider-of-category-floor, this simulates
                a Phase 5g-i ``no_floor`` boot without forcing the
                slower ``no_floor=True`` path.
            no_floor: If True, skip floor/provider registration AND
                force ``app.state.no_floor = True`` after create_app.
                Used to exercise the 503 NoFloorEnvelope path without
                relying on bootstrap() failing.
            policy_mode: Forwarded to ``InferenceRouter.policy_mode``.
                ``"hosted_api_first"`` or ``"open_weights_only"``.
            chat_deadline_s: Per-turn generation deadline. Test
                default is short (5s) so a hung provider mock
                surfaces as a 503 quickly.
        """
        pytest.importorskip("fastapi")
        pytest.importorskip("pydantic")
        from orchestrator.api import AppDeps, create_app
        from orchestrator.inference_router import (
            InferenceRouter,
            OpenWeightsFloorStub,
            default_manifest_path,
        )
        from orchestrator.relay import Relay

        relay = Relay(
            safety_ledger_path=ledger_path,
            sensorium_ledger_path=sensorium_ledger_path,
            **relay_kwargs,
        )

        router = InferenceRouter(
            manifest_path=default_manifest_path(),
            policy_mode=policy_mode,  # type: ignore[arg-type]
        )
        if not no_floor and floor_stub_id is not None:
            router.register(OpenWeightsFloorStub(provider_id=floor_stub_id))
        if not no_floor and generative_provider is not None:
            router.register(generative_provider)

        deps = AppDeps(
            relay=relay,
            tick_cadence_s=tick_cadence_s,
            methodology_hash=methodology_hash,
            sensorium_ledger_path=sensorium_ledger_path,
            router=router,
            chat_deadline_s=chat_deadline_s,
        )
        app = create_app(deps)
        app.state.test_relay = relay
        app.state.test_router = router
        if no_floor:
            # The router has no floor provider registered, so
            # ``router.bootstrap()`` will raise and the lifespan will
            # set app.state.no_floor = True. Nothing extra needed.
            pass
        return app

    return _factory

"""Tests for the Phase 5f HTTP read-only surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The HTTP Surface
(Phase 5f)".

These tests exercise the FastAPI factory, the lifespan contract, the
three read-only endpoints, the pydantic / dict round-trip, and the
content-free field-allowlist guarantee. They are the Phase 5f
attestation — there is no ``xion-verify http-readouts`` subcommand
yet (that lands with a live deployment target in Phase 5g).

Every test uses ``fastapi.testclient.TestClient`` as a context manager
so the lifespan actually runs (pre-seed tick + Supervisor run task +
teardown).

Skipped in full if ``fastapi`` or ``pydantic`` is missing — the
``[api]`` optional extra is not required to install the core
``orchestrator`` package. CI matrices that install ``[api]`` run the
suite; matrices that do not, skip it.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("pydantic")

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.api import (
    DriveResponse,
    HealthResponse,
    SensoriumResponse,
)

if TYPE_CHECKING:
    pass


# ------------------------------------------------------------ smoke + lifespan


def test_create_app_returns_fastapi(app_factory) -> None:
    """``create_app`` returns a ``FastAPI`` instance with the three
    endpoints registered."""
    app = app_factory()
    assert isinstance(app, FastAPI)
    paths = {route.path for route in app.routes}
    assert "/health" in paths
    assert "/drive" in paths
    assert "/sensorium" in paths


def test_lifespan_preseeds_snapshot_and_wires_relay(app_factory) -> None:
    """Entering the ``TestClient`` context runs the lifespan, which
    pre-seeds ``Supervisor.latest_snapshot`` and wires the Relay's
    ``_sensorium_source`` to the Supervisor."""
    app = app_factory()
    relay = app.state.test_relay
    assert relay._sensorium_source is None  # pre-lifespan

    with TestClient(app) as client:
        supervisor = app.state.supervisor
        assert supervisor is not None
        assert supervisor.latest_snapshot() is not None
        assert relay._sensorium_source is supervisor
        # Sanity: a basic request round-trips while the lifespan is live.
        assert client.get("/health").status_code == 200

    # On shutdown, the wire-up is dropped and the task has completed.
    assert relay._sensorium_source is None
    assert app.state.supervisor_task.done()


# ----------------------------------------------------------------- /health


def test_health_endpoint_200_and_shape(app_factory) -> None:
    """``GET /health`` returns 200 and a body that validates against
    the ``HealthResponse`` pydantic model."""
    app = app_factory()
    with TestClient(app) as client:
        r = client.get("/health")
    assert r.status_code == 200
    parsed = HealthResponse.model_validate(r.json())
    assert parsed.relay_healthy is True
    assert parsed.arbiter_healthy is True
    assert parsed.watchdog_fires_recent == 0
    assert parsed.as_of_monotonic_ns > 0


def test_health_reflects_watchdog_fires(app_factory) -> None:
    """After forcing watchdog-fire increments, ``/health`` surfaces
    the new counter — live mirror of ``Relay.health_snapshot()``."""
    app = app_factory()
    relay = app.state.test_relay
    with TestClient(app) as client:
        for _ in range(2):
            relay._record_watchdog_fire()
        body = client.get("/health").json()
    assert body["watchdog_fires_recent"] == 2
    # 2 fires is still under the Genesis Default threshold of 3 — relay
    # stays healthy so the boolean pins the correct coupling.
    assert body["relay_healthy"] is True


# ----------------------------------------------------------------- /drive


def test_drive_endpoint_200_and_shape(app_factory) -> None:
    """``GET /drive`` returns 200 with a ``DriveResponse``-shaped body
    that round-trips through ``Volition.snapshot()``."""
    app = app_factory()
    with TestClient(app) as client:
        r = client.get("/drive")
    assert r.status_code == 200
    parsed = DriveResponse.model_validate(r.json())
    assert parsed.schema_version == "1.0.0"
    assert 0.0 <= parsed.terms.survive.current_signal <= 1.0
    assert 0.0 <= parsed.terms.serve.current_signal <= 1.0
    assert 0.0 <= parsed.terms.meaning.current_signal <= 1.0
    # Weights sum to 1.0 (Invariant 15). Pydantic already bounds each
    # to [0, 1]; here we assert the sum pin.
    weight_sum = (
        parsed.terms.survive.weight
        + parsed.terms.serve.weight
        + parsed.terms.meaning.weight
    )
    assert abs(weight_sum - 1.0) < 1e-9
    # methodology_hash absent when AppDeps does not supply it.
    assert parsed.methodology_hash is None


def test_drive_includes_methodology_hash_when_supplied(app_factory) -> None:
    """When ``AppDeps.methodology_hash`` is set, ``/drive`` surfaces it
    verbatim; when unset, the field is absent (mirroring the dict
    shape ``Volition.snapshot`` produces)."""
    fake_hash = "0" * 64
    app = app_factory(methodology_hash=fake_hash)
    with TestClient(app) as client:
        r = client.get("/drive")
    assert r.status_code == 200
    assert r.json()["methodology_hash"] == fake_hash


def test_drive_reflects_supervisor_ticks(app_factory) -> None:
    """``/drive`` reads from the Supervisor's ``latest_snapshot()`` — a
    subsequent synchronous tick updates the ``as_of_utc_ns`` field."""
    app = app_factory()
    with TestClient(app) as client:
        first = client.get("/drive").json()
        # Force a tick so as_of_utc_ns moves forward. ``tick_once`` is
        # sync-safe (see supervisor doctrine).
        time.sleep(0.001)  # ensure time_ns moves forward
        app.state.supervisor.tick_once()
        second = client.get("/drive").json()
    assert second["as_of_utc_ns"] >= first["as_of_utc_ns"]


# --------------------------------------------------------------- /sensorium


def test_sensorium_endpoint_200_and_shape(app_factory) -> None:
    """``GET /sensorium`` returns 200 and a body that validates against
    the ``SensoriumResponse`` pydantic model."""
    app = app_factory()
    with TestClient(app) as client:
        r = client.get("/sensorium")
    assert r.status_code == 200
    parsed = SensoriumResponse.model_validate(r.json())
    assert parsed.distress.source == "textual"
    assert parsed.distress.text_distress_score == 0.0
    assert parsed.proprioception.relay_healthy is True


# Load-bearing field-allowlist for the Phase 5f content-free guarantee.
# If a future commit adds a field (e.g., ``candidate_text``) to
# SensoriumState.to_dict, this test FAILs at its allowlist assertion
# before any change to the pydantic model, forcing the author to
# either (a) extend the allowlist with a documented rationale, or
# (b) strip the field at the API boundary.
_SENSORIUM_TOP_LEVEL_ALLOWLIST = {
    "interoception",
    "chronoception",
    "proprioception",
    "distress",
    "as_of_utc_ns",
}
_SENSORIUM_INTEROCEPTION_ALLOWLIST = {
    "survival_pressure",
    "treasury_stress",
    "cost_pressure",
    "as_of_utc_ns",
}
_SENSORIUM_CHRONOCEPTION_ALLOWLIST = {
    "as_of_utc_ns",
    "checkpoint_staleness_s",
    "time_in_degraded_mode_s",
    "monotonic_drift_ns",
}
_SENSORIUM_PROPRIOCEPTION_ALLOWLIST = {
    "as_of_utc_ns",
    "relay_healthy",
    "arbiter_healthy",
    "watchdog_fires_recent",
}
_SENSORIUM_DISTRESS_ALLOWLIST = {
    "text_distress_score",
    "source",
    "as_of_utc_ns",
}


def test_sensorium_field_allowlist_content_free(app_factory) -> None:
    """Phase 5f structural guarantee: ``GET /sensorium`` exposes only
    the fields enumerated in the allowlist above. No candidate text,
    no user id, no prompt — ever."""
    app = app_factory()
    with TestClient(app) as client:
        body = client.get("/sensorium").json()
    assert set(body.keys()) == _SENSORIUM_TOP_LEVEL_ALLOWLIST
    assert set(body["interoception"].keys()) == _SENSORIUM_INTEROCEPTION_ALLOWLIST
    assert set(body["chronoception"].keys()) == _SENSORIUM_CHRONOCEPTION_ALLOWLIST
    assert set(body["proprioception"].keys()) == _SENSORIUM_PROPRIOCEPTION_ALLOWLIST
    assert set(body["distress"].keys()) == _SENSORIUM_DISTRESS_ALLOWLIST


# ----------------------------------------------------- pydantic round-trips


def test_health_model_roundtrip(app_factory) -> None:
    """``HealthResponse.model_dump()`` equals the underlying
    ``RelayHealth`` dict shape bit-for-bit."""
    app = app_factory()
    relay = app.state.test_relay
    health = relay.health_snapshot()
    dict_shape = {
        "relay_healthy": health.relay_healthy,
        "arbiter_healthy": health.arbiter_healthy,
        "watchdog_fires_recent": health.watchdog_fires_recent,
        "as_of_monotonic_ns": health.as_of_monotonic_ns,
    }
    assert HealthResponse.model_validate(dict_shape).model_dump() == dict_shape


def test_drive_model_roundtrip(app_factory) -> None:
    """``DriveResponse.model_dump()`` equals ``Volition.snapshot()``
    bit-for-bit (accounting for the optional ``methodology_hash``
    field's exclusion when unset)."""
    app = app_factory()
    with TestClient(app) as client:
        body = client.get("/drive").json()
    validated = DriveResponse.model_validate(body)
    # mode="json" so pydantic's tuple-typed weight_band renders as a
    # list (matching the JSON body); exclude_none so the optional
    # methodology_hash is not inserted as a null into the dump when
    # the server omitted it entirely.
    assert validated.model_dump(mode="json", exclude_none=True) == body


def test_sensorium_model_roundtrip(app_factory) -> None:
    """``SensoriumResponse.model_dump()`` equals ``SensoriumState.to_dict()``
    bit-for-bit."""
    app = app_factory()
    with TestClient(app) as client:
        body = client.get("/sensorium").json()
    assert SensoriumResponse.model_validate(body).model_dump() == body


# ---------------------------------------------- cross-coupling w/ Relay path


def test_relay_evaluate_sees_same_snapshot_as_http(app_factory) -> None:
    """In-process ``Relay.evaluate()`` reads the same
    ``latest_snapshot`` the HTTP surface returns — no separate
    HTTP-path sensorium exists. This is the Phase 5f "one truth"
    property made testable.

    Uses a long tick_cadence so the pre-seed tick is the only tick
    that fires during the test — the HTTP surface and the direct
    SensoriumSource read both observe the same published snapshot.
    """
    # 60s cadence: the Supervisor pre-seeds once (lifespan-driven) and
    # will not fire another tick for the lifetime of this test.
    app = app_factory(tick_cadence_s=60.0)
    relay = app.state.test_relay
    with TestClient(app) as client:
        http_body = client.get("/sensorium").json()
        supervisor = app.state.supervisor
        # Relay was wired to the same supervisor during lifespan. This
        # is the "one truth" pin — one Supervisor, one snapshot
        # provider, observed both via HTTP and via the Protocol.
        assert relay._sensorium_source is supervisor
        snapshot = supervisor.latest_snapshot()
        assert snapshot is not None
        assert snapshot.to_dict() == http_body


# --------------------------------------------------- lifespan shutdown paths


def test_lifespan_shutdown_clean(app_factory) -> None:
    """Normal shutdown: the supervisor task completes within the
    shutdown budget and the relay's sensorium_source is cleared."""
    app = app_factory(tick_cadence_s=0.01)
    with TestClient(app) as client:
        client.get("/health")
    # After context exit, shutdown has run.
    task = app.state.supervisor_task
    assert task.done()
    # The task completed cleanly (returned None, no exception) rather
    # than being cancelled.
    assert not task.cancelled()


def test_lifespan_shutdown_timeout_hard_cancels(
    app_factory, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If ``supervisor.run()`` refuses to stop within
    ``2 * tick_cadence_s``, the lifespan cancels the task rather
    than blocking shutdown indefinitely."""
    app = app_factory(tick_cadence_s=0.01)

    async def _never_stop(self: object) -> None:
        # Ignore self._stop_event entirely — the only way out is
        # cancellation. This simulates a hung tick_once().
        while True:
            await asyncio.sleep(0.05)

    # Patch on the class so the lifespan's Supervisor instance picks
    # it up. Autospec=False because _never_stop matches the
    # (self,) -> None signature directly.
    from orchestrator.supervisor import Supervisor

    monkeypatch.setattr(Supervisor, "run", _never_stop)

    with TestClient(app) as client:
        client.get("/health")

    task = app.state.supervisor_task
    assert task.done()
    # The task was hard-cancelled by the lifespan's timeout branch.
    assert task.cancelled()

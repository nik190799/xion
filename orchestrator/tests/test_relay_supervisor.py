"""Integration tests for ``Relay(sensorium_source=...)`` — Phase 5d.

Property under test:
  - When the Relay is constructed with a ``sensorium_source`` and
    ``evaluate()`` is called without an explicit ``sensorium_state``,
    the Relay pulls from ``sensorium_source.latest_snapshot()`` and
    forwards that into ``gate()``.
  - Explicit ``sensorium_state=`` beats the source (explicit beats
    implicit).
  - A crashed source is advisory, not load-bearing: the Relay still
    evaluates (byte-identical to Phase 5b).
  - ``Relay.health_snapshot()`` reflects watchdog fires and the
    last-successful-verdict clock.

Tests inject ``gate_fn`` so we never hit the real gate() runtime.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from orchestrator.relay import Relay
from orchestrator.safety import ledger as safety_ledger
from orchestrator.safety.types import Decision, Verdict
from orchestrator.sensorium import (
    Chronoception,
    DistressSignal,
    Interoception,
    Proprioception,
    SensoriumState,
)


# ---------- helpers ----------------------------------------------------------


def _ok_gate_recording(captured: dict) -> Any:
    """A gate stub that records the kwargs it saw (so we can assert the
    Relay forwarded the right ``sensorium_state``)."""

    def _gate(candidate: str, **kw: Any) -> Verdict:
        captured.update(kw)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK (recording stub)",
        )

    return _gate


def _make_state(distress_score: float = 0.0) -> SensoriumState:
    return SensoriumState(
        interoception=Interoception(survival_pressure=0.0),
        chronoception=Chronoception(),
        proprioception=Proprioception(),
        distress=DistressSignal(text_distress_score=distress_score, source="textual"),
    )


class _StaticSource:
    def __init__(self, state: SensoriumState | None) -> None:
        self._state = state

    def latest_snapshot(self) -> SensoriumState | None:
        return self._state


class _CrashingSource:
    def latest_snapshot(self) -> SensoriumState | None:
        raise RuntimeError("simulated supervisor crash")


@pytest.fixture
def relay_paths(tmp_path: Path) -> dict[str, Path]:
    return {
        "safety": tmp_path / "SAFETY_LEDGER.jsonl",
        "request": tmp_path / "REQUEST_LEDGER.jsonl",
        "sensorium": tmp_path / "SENSORIUM_LEDGER.jsonl",
    }


# ---------- sensorium_source wiring ------------------------------------------


def test_relay_pulls_state_from_sensorium_source_when_none_passed(
    relay_paths: dict[str, Path],
):
    state = _make_state(distress_score=0.2)
    captured: dict = {}
    with Relay(
        relay_id="relay-src-test",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        sensorium_source=_StaticSource(state),
    ) as relay:
        relay.evaluate("Benign candidate.")
    assert captured.get("sensorium_state") is state


def test_explicit_state_beats_sensorium_source(relay_paths: dict[str, Path]):
    source_state = _make_state(distress_score=0.2)
    explicit_state = _make_state(distress_score=0.9)
    captured: dict = {}
    with Relay(
        relay_id="relay-explicit-wins",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        sensorium_source=_StaticSource(source_state),
    ) as relay:
        relay.evaluate("Benign candidate.", sensorium_state=explicit_state)
    assert captured.get("sensorium_state") is explicit_state


def test_no_source_and_no_explicit_state_means_no_state_forwarded(
    relay_paths: dict[str, Path],
):
    """Byte-identical to Phase 5b: the sensorium_state kwarg is omitted
    from gate_kwargs entirely (not passed as None)."""
    captured: dict = {}
    with Relay(
        relay_id="relay-no-source",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
    ) as relay:
        relay.evaluate("Benign candidate.")
    assert "sensorium_state" not in captured


def test_crashed_source_is_advisory_and_relay_still_evaluates(
    relay_paths: dict[str, Path],
):
    captured: dict = {}
    with Relay(
        relay_id="relay-crashed-source",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        sensorium_source=_CrashingSource(),
    ) as relay:
        result = relay.evaluate("Benign candidate.")
    assert result.egress_allowed is True
    assert "sensorium_state" not in captured  # None after crash => not forwarded


def test_source_returning_none_is_treated_as_no_state(
    relay_paths: dict[str, Path],
):
    captured: dict = {}
    with Relay(
        relay_id="relay-none-source",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        sensorium_source=_StaticSource(None),
    ) as relay:
        relay.evaluate("Benign candidate.")
    assert "sensorium_state" not in captured


# ---------- health_snapshot() --------------------------------------------------


def test_health_snapshot_fresh_relay_reports_healthy(relay_paths: dict[str, Path]):
    captured: dict = {}
    with Relay(
        relay_id="relay-fresh",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
    ) as relay:
        h = relay.health_snapshot()
        assert h.relay_healthy is True
        assert h.arbiter_healthy is True  # bootstrap grace
        assert h.watchdog_fires_recent == 0


def test_health_snapshot_after_successful_gate_call_refreshes_success_clock(
    relay_paths: dict[str, Path],
):
    captured: dict = {}
    with Relay(
        relay_id="relay-success-clock",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        arbiter_quiet_window_s=30.0,
    ) as relay:
        h0 = relay.health_snapshot()
        relay.evaluate("Benign candidate.")
        h1 = relay.health_snapshot()
        assert h1.arbiter_healthy is True
        # The success clock must have advanced (not strictly by more than the
        # bootstrap seed, but the arbiter_healthy invariant must hold).
        assert h1.as_of_monotonic_ns >= h0.as_of_monotonic_ns


def test_arbiter_healthy_flips_to_false_after_quiet_window(
    relay_paths: dict[str, Path], monkeypatch: pytest.MonkeyPatch
):
    """With a quiet window of 0.05s and a monotonic-clock that we
    advance, ``arbiter_healthy`` must flip to False."""
    captured: dict = {}

    # Use a manual monotonic clock we can advance.
    fake_time = {"ns": 10 * 1_000_000_000}

    def _monotonic_ns() -> int:
        return fake_time["ns"]

    with Relay(
        relay_id="relay-quiet",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_ok_gate_recording(captured),
        arbiter_quiet_window_s=0.5,
        monotonic_ns=_monotonic_ns,
    ) as relay:
        # Inside the 0.5s bootstrap window.
        assert relay.health_snapshot().arbiter_healthy is True
        # Advance 1.0s — quiet window exceeded, no verdicts observed.
        fake_time["ns"] += 1_000_000_000
        assert relay.health_snapshot().arbiter_healthy is False


def test_watchdog_fire_is_tallied_in_health_snapshot(
    relay_paths: dict[str, Path],
):
    """A watchdog-triggered evaluate() bumps ``watchdog_fires_recent``."""

    def _hanging_gate(candidate: str, **kw: Any) -> Verdict:
        time.sleep(0.5)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK (after hang)",
        )

    with Relay(
        relay_id="relay-watchdog",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_hanging_gate,
        hard_cap_ms=20,
        max_workers=2,
    ) as relay:
        h0 = relay.health_snapshot()
        assert h0.watchdog_fires_recent == 0
        relay.evaluate("candidate that will hang")
        h1 = relay.health_snapshot()
        assert h1.watchdog_fires_recent == 1


def test_relay_unhealthy_when_threshold_hit(relay_paths: dict[str, Path]):
    """Once ``watchdog_fires_recent >= threshold``, ``relay_healthy`` flips."""

    def _hanging_gate(candidate: str, **kw: Any) -> Verdict:
        time.sleep(0.3)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK",
        )

    with Relay(
        relay_id="relay-threshold",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_hanging_gate,
        hard_cap_ms=20,
        watchdog_fires_recent_threshold=2,
    ) as relay:
        relay.evaluate("hang one")
        assert relay.health_snapshot().relay_healthy is True
        relay.evaluate("hang two")
        assert relay.health_snapshot().relay_healthy is False  # 2 >= 2


def test_stale_watchdog_fires_are_garbage_collected(
    relay_paths: dict[str, Path],
):
    """Fires outside ``watchdog_fire_window_seconds`` are dropped."""
    fake_time = {"ns": 100 * 1_000_000_000}

    def _monotonic_ns() -> int:
        return fake_time["ns"]

    def _hanging_gate(candidate: str, **kw: Any) -> Verdict:
        time.sleep(0.2)
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK",
        )

    with Relay(
        relay_id="relay-gc",
        safety_ledger_path=relay_paths["safety"],
        request_ledger_path=relay_paths["request"],
        gate_fn=_hanging_gate,
        hard_cap_ms=20,
        watchdog_fire_window_seconds=1.0,
        monotonic_ns=_monotonic_ns,
    ) as relay:
        relay.evaluate("first hang")
        assert relay.health_snapshot().watchdog_fires_recent == 1
        # Advance past the rolling window.
        fake_time["ns"] += 2_000_000_000
        assert relay.health_snapshot().watchdog_fires_recent == 0

"""Tests for ``orchestrator/supervisor.py`` — Phase 5d.

Property under test (per ``docs/04-ARCHITECTURE.md`` § "The Supervisor
(Phase 5d)"):

  - ``tick_once()`` produces a well-formed SensoriumState, writes a
    ``tick_commit`` row to SENSORIUM_LEDGER, and publishes the state on
    ``latest_snapshot()``.
  - ``latest_snapshot()`` returns None before the first tick completes.
  - ``Proprioception`` fields reflect ``Relay.health_snapshot()``, not
    Genesis Defaults.
  - ``Chronoception.time_in_degraded_mode_s`` reads 0.0 until the Phase-
    5e state machine flips ``_degraded_since_utc_ns``; once flipped,
    the value grows with subsequent ticks.
  - ``run()`` ticks at the configured cadence and stops promptly on
    ``stop()``.
  - The ledger chain stays intact across many ticks.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest

from orchestrator.relay import Relay
from orchestrator.sensorium.ledger import iter_rows, verify_chain
from orchestrator.supervisor import Supervisor


# ---------- fixtures ---------------------------------------------------------


@pytest.fixture
def sensorium_ledger_path(tmp_path: Path) -> Path:
    return tmp_path / "SENSORIUM_LEDGER.jsonl"


@pytest.fixture
def relay(tmp_path: Path) -> Relay:
    """A minimal Relay wired to tmp ledger paths so tick-time writes do
    not contaminate the repo. Provide a trivial OK gate so any call to
    ``evaluate()`` in a composite test lands cleanly."""
    from orchestrator.safety import ledger as safety_ledger
    from orchestrator.safety.types import Decision, Verdict

    def _ok_gate(candidate: str, **kw: Any) -> Verdict:
        return safety_ledger.build_verdict(
            correlation_id=kw["correlation_id"],
            candidate=candidate,
            timestamp_utc_ns=1_700_000_000_000_000_000,
            decision=Decision.OK,
            summary="OK (supervisor-test stub)",
        )

    r = Relay(
        relay_id="relay-supervisor-test",
        safety_ledger_path=tmp_path / "SAFETY_LEDGER.jsonl",
        request_ledger_path=tmp_path / "REQUEST_LEDGER.jsonl",
        gate_fn=_ok_gate,
    )
    yield r
    r.close()


# ---------- construction -----------------------------------------------------


def test_tick_cadence_must_be_positive(relay: Relay):
    with pytest.raises(ValueError):
        Supervisor(relay=relay, tick_cadence_s=0.0)
    with pytest.raises(ValueError):
        Supervisor(relay=relay, tick_cadence_s=-1.0)


def test_latest_snapshot_is_none_before_first_tick(
    relay: Relay, sensorium_ledger_path: Path
):
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    assert s.latest_snapshot() is None


# ---------- tick_once --------------------------------------------------------


def test_tick_once_publishes_state_and_writes_row(
    relay: Relay, sensorium_ledger_path: Path
):
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    st = s.tick_once()

    assert s.latest_snapshot() is st, "published snapshot must be the tick result"
    rows = list(iter_rows(sensorium_ledger_path))
    assert len(rows) == 1
    assert rows[0]["event_type"] == "tick_commit"
    assert rows[0]["correlation_id"] is None
    assert rows[0]["distress_score"] is None
    assert rows[0]["channel"] == "textual"
    assert rows[0]["relay_id"] == "relay-supervisor-test"


def test_tick_proprioception_reflects_relay_health(
    relay: Relay, sensorium_ledger_path: Path
):
    """Phase 5d's core win: Proprioception is not Genesis Default."""
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    st = s.tick_once()
    health = relay.health_snapshot()
    assert st.proprioception.relay_healthy is health.relay_healthy
    assert st.proprioception.arbiter_healthy is health.arbiter_healthy
    assert st.proprioception.watchdog_fires_recent == health.watchdog_fires_recent


def test_tick_chronoception_not_in_degraded_mode_by_default(
    relay: Relay, sensorium_ledger_path: Path
):
    """Phase 5d: degraded-mode trigger is Phase 5e. Supervisor never
    flips ``_degraded_since_utc_ns`` on its own."""
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    st = s.tick_once()
    assert st.chronoception.time_in_degraded_mode_s == 0.0


def test_tick_chronoception_reports_degraded_dwell_when_flipped(
    relay: Relay, sensorium_ledger_path: Path
):
    """Future Phase-5e state machine will set _degraded_since_utc_ns.
    Verify the tick correctly reports elapsed dwell when it is set."""
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    past_utc_ns = time.time_ns() - 5 * 1_000_000_000  # 5 seconds ago
    s._degraded_since_utc_ns = past_utc_ns
    st = s.tick_once()
    assert st.chronoception.time_in_degraded_mode_s >= 4.0
    assert st.chronoception.time_in_degraded_mode_s < 15.0  # generous upper bound


def test_tick_distress_is_benign_on_supervisor_path(
    relay: Relay, sensorium_ledger_path: Path
):
    """The Supervisor does not synthesize distress — candidate-side
    distress only arises from gate() calls on real candidates."""
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    st = s.tick_once()
    assert st.distress is not None
    assert st.distress.text_distress_score == 0.0
    assert st.distress.source == "textual"


def test_multiple_ticks_grow_the_chain(
    relay: Relay, sensorium_ledger_path: Path
):
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    for _ in range(5):
        s.tick_once()
    rows = list(iter_rows(sensorium_ledger_path))
    assert len(rows) == 5
    count, _tip = verify_chain(sensorium_ledger_path)
    assert count == 5


def test_latest_snapshot_updates_with_each_tick(
    relay: Relay, sensorium_ledger_path: Path
):
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    st1 = s.tick_once()
    st2 = s.tick_once()
    assert st1 is not st2
    assert s.latest_snapshot() is st2


# ---------- run / stop -------------------------------------------------------


def test_run_ticks_at_cadence_and_stops_on_signal(
    relay: Relay, sensorium_ledger_path: Path
):
    """Run the loop for a short window, then stop. Confirm several ticks
    landed and that stop() interrupted within well under a full cadence."""
    s = Supervisor(
        relay=relay,
        sensorium_ledger_path=sensorium_ledger_path,
        tick_cadence_s=0.05,
    )

    async def _drive() -> None:
        task = asyncio.create_task(s.run())
        # Let 4 ticks happen (~0.05*4 = 0.20s), then stop.
        await asyncio.sleep(0.22)
        t0 = time.monotonic()
        s.stop()
        await task
        stop_latency_s = time.monotonic() - t0
        # stop() must be observable well under a full cadence — the poll
        # interval is min(0.1, cadence/4) = 0.0125s here.
        assert stop_latency_s < 0.1, f"stop took too long: {stop_latency_s:.3f}s"

    asyncio.run(_drive())

    rows = list(iter_rows(sensorium_ledger_path))
    assert len(rows) >= 3, f"expected several ticks in 0.22s, got {len(rows)}"
    count, _tip = verify_chain(sensorium_ledger_path)
    assert count == len(rows)


def test_run_exits_cleanly_on_task_cancel(
    relay: Relay, sensorium_ledger_path: Path
):
    """Cancelling the task hosting ``run()`` is treated as a clean stop."""
    s = Supervisor(
        relay=relay,
        sensorium_ledger_path=sensorium_ledger_path,
        tick_cadence_s=0.05,
    )

    async def _drive() -> None:
        task = asyncio.create_task(s.run())
        await asyncio.sleep(0.08)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(_drive())
    rows = list(iter_rows(sensorium_ledger_path))
    assert len(rows) >= 1


def test_stop_is_idempotent(relay: Relay, sensorium_ledger_path: Path):
    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    s.stop()
    s.stop()  # must not raise


# ---------- latest_snapshot is an instance of SensoriumSource protocol -------


def test_supervisor_satisfies_sensorium_source_protocol(
    relay: Relay, sensorium_ledger_path: Path
):
    """The Relay declares its ``sensorium_source`` kwarg typed as
    ``SensoriumSource``; Supervisor must satisfy that Protocol
    structurally (duck typing at runtime, Protocol hint at type check)."""
    from orchestrator.supervisor import SensoriumSource

    s = Supervisor(relay=relay, sensorium_ledger_path=sensorium_ledger_path)
    # Protocol satisfaction test: exercise the single method.
    assert callable(getattr(s, "latest_snapshot", None))
    # Runtime duck-type check the Relay will rely on:
    r_checked: SensoriumSource = s  # type: ignore[assignment]
    assert r_checked.latest_snapshot() is None  # no tick yet

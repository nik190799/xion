"""Phase 5g+ multi-worker integration tests for the broker-wired Supervisor.

Doctrine anchors:

- ``docs/04-ARCHITECTURE.md`` § "Multi-worker coherence (Phase 5g+)"
- ``docs/33-MULTI-WORKER.md`` § "Lease semantics"

These tests spin up two *in-process* ``BrokerSupervisorShell`` instances
sharing one ``SqliteBroker`` (one broker DB file on tmp_path). They prove:

- **Single-leader invariant.** Only one shell ticks at a time; exactly one
  ``relay_id`` appears in the ``SENSORIUM_LEDGER`` ``tick_commit`` stream
  over a representative window.
- **Snapshot publish/subscribe.** The follower shell's ``latest_snapshot()``
  round-trips through the broker to a ``SensoriumState`` identical in shape
  to the leader's local snapshot.
- **Leader failover.** When the leader stops, the follower promotes itself
  within ``leader_lease_s`` + the follower's poll cadence and starts ticking.

We do **not** spawn uvicorn subprocesses here — uvicorn's multi-worker path
is exercised by the launcher runbook, not by unit tests. The in-process
two-shell simulation is faithful because the broker is the single point
of coherence: if two shells sharing the same broker DB honor the
single-leader invariant, so do two uvicorn workers (they use the identical
``BrokerSupervisorShell`` + ``SqliteBroker`` code path).
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from orchestrator.relay import Relay
from orchestrator.runtime import (
    BrokerConfig,
    BrokerSupervisorShell,
    SqliteBroker,
    deserialize_sensorium_state,
)
from orchestrator.supervisor import Supervisor

# --- Fixtures -------------------------------------------------------------


@pytest.fixture()
def shared_broker_path(tmp_path: Path) -> Path:
    """Shared SQLite broker file across two simulated workers."""
    return tmp_path / "broker.sqlite3"


@pytest.fixture()
def shared_sensorium_ledger_path(tmp_path: Path) -> Path:
    """Shared SENSORIUM_LEDGER file the leader appends to."""
    return tmp_path / "SENSORIUM_LEDGER.jsonl"


def _make_broker(db_path: Path) -> SqliteBroker:
    """Construct a short-lease SqliteBroker tuned for fast failover in tests."""
    config = BrokerConfig(
        db_path=db_path,
        leader_lease_s=0.5,
        leader_renew_s=0.1,
        busy_timeout_ms=5000,
    )
    return SqliteBroker(config=config)


def _make_shell(
    broker: SqliteBroker,
    *,
    worker_id: str,
    sensorium_ledger_path: Path,
    tick_cadence_s: float,
    relay_id: str | None = None,
) -> BrokerSupervisorShell:
    """Build a shell around a fresh Relay. Each shell owns its own Relay
    instance (uvicorn workers are separate processes each with their own
    Relay). A distinct ``relay_id`` is required in multi-shell tests so
    the SENSORIUM_LEDGER ``tick_commit`` rows distinguish leaders from
    promoted-followers in failover scenarios (Relay's default relay_id
    is the same constant across construction; we pass an explicit id)."""
    relay = Relay(relay_id=relay_id if relay_id is not None else f"relay-{worker_id}")
    return BrokerSupervisorShell(
        broker=broker,
        worker_id=worker_id,
        leader_renew_s=0.1,
        supervisor_factory=Supervisor,
        sensorium_ledger_path=sensorium_ledger_path,
        tick_cadence_s=tick_cadence_s,
        relay=relay,
        follower_poll_s=0.05,
    )


def _read_tick_commits(path: Path) -> list[dict]:
    """Parse the SENSORIUM_LEDGER and return only tick_commit rows."""
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if row.get("event_type") == "tick_commit":
            rows.append(row)
    return rows


# --- Single-leader invariant ---------------------------------------------


class TestSingleLeaderInvariant:
    """Property P2 from ``docs/04-ARCHITECTURE.md`` § "Multi-worker coherence":
    exactly one worker ticks at a time. With two shells sharing one broker,
    the SENSORIUM_LEDGER's ``tick_commit`` stream over a representative
    window must name exactly one ``relay_id``."""

    def test_two_shells_one_broker_single_relay_id_dominates(
        self,
        shared_broker_path: Path,
        shared_sensorium_ledger_path: Path,
    ) -> None:
        broker_a = _make_broker(shared_broker_path)
        broker_b = _make_broker(shared_broker_path)

        async def _drive() -> None:
            shell_a = _make_shell(
                broker_a,
                worker_id="worker-a",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )
            shell_b = _make_shell(
                broker_b,
                worker_id="worker-b",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )

            # Seed both; exactly one should become leader.
            shell_a.initial_seed()
            shell_b.initial_seed()
            roles = {shell_a.worker_id: shell_a.role, shell_b.worker_id: shell_b.role}
            assert sorted(roles.values()) == ["follower", "leader"], roles

            # Run both for long enough to collect a representative window.
            task_a = asyncio.create_task(shell_a.run())
            task_b = asyncio.create_task(shell_b.run())
            try:
                await asyncio.sleep(0.35)  # many ticks at cadence 0.05s
            finally:
                shell_a.stop()
                shell_b.stop()
                await asyncio.wait_for(task_a, timeout=2.0)
                await asyncio.wait_for(task_b, timeout=2.0)

        try:
            asyncio.run(_drive())
        finally:
            broker_a.close()
            broker_b.close()

        rows = _read_tick_commits(shared_sensorium_ledger_path)
        # At least a few ticks should have committed.
        assert len(rows) >= 3, f"expected multiple ticks, got {len(rows)}"

        # Exactly one relay_id dominates the window. In the no-failover case
        # we expect one unique relay_id end-to-end.
        relay_ids = {row["relay_id"] for row in rows}
        assert len(relay_ids) == 1, (
            f"two relay_ids ticked concurrently, corrupting cadence: {relay_ids}"
        )


# --- Snapshot publish/subscribe ------------------------------------------


class TestSnapshotPublishSubscribe:
    """Property P1 — broker-backed leader publishes state.to_dict() on every
    tick; the follower's latest_snapshot() deserializes it back to a
    SensoriumState with the same shape as the leader's local snapshot."""

    def test_follower_snapshot_matches_leader_snapshot_shape(
        self,
        shared_broker_path: Path,
        shared_sensorium_ledger_path: Path,
    ) -> None:
        broker_a = _make_broker(shared_broker_path)
        broker_b = _make_broker(shared_broker_path)

        async def _drive() -> None:
            shell_a = _make_shell(
                broker_a,
                worker_id="worker-a",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )
            shell_b = _make_shell(
                broker_b,
                worker_id="worker-b",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )
            shell_a.initial_seed()
            shell_b.initial_seed()

            leader, follower = (
                (shell_a, shell_b)
                if shell_a.role == "leader"
                else (shell_b, shell_a)
            )
            assert leader.role == "leader"
            assert follower.role == "follower"

            task_leader = asyncio.create_task(leader.run())
            task_follower = asyncio.create_task(follower.run())

            try:
                # Give the leader time to publish at least one snapshot
                # past its initial_seed tick.
                await asyncio.sleep(0.2)

                leader_snap = leader.latest_snapshot()
                follower_snap = follower.latest_snapshot()
                assert leader_snap is not None
                assert follower_snap is not None

                # Shape-equality via the documented round-trip:
                # dict → deserialize_sensorium_state → dict.
                assert (
                    follower_snap.interoception.survival_pressure
                    == leader_snap.interoception.survival_pressure
                )
                assert (
                    follower_snap.proprioception.relay_healthy
                    == leader_snap.proprioception.relay_healthy
                )

                # Round-trip stability: a follower's snapshot re-serialized
                # and re-deserialized must equal the original.
                payload = follower_snap.to_dict()
                reroundtripped = deserialize_sensorium_state(payload)
                assert reroundtripped.to_dict() == payload
            finally:
                leader.stop()
                follower.stop()
                await asyncio.wait_for(task_leader, timeout=2.0)
                await asyncio.wait_for(task_follower, timeout=2.0)

        try:
            asyncio.run(_drive())
        finally:
            broker_a.close()
            broker_b.close()


# --- Leader failover ------------------------------------------------------


class TestLeaderFailover:
    """Property P2 failover clause: if the leader stops, the follower promotes
    itself within ``leader_lease_s`` + follower poll cadence and begins
    ticking under its own ``relay_id``.

    The test validates this by stopping the leader, waiting slightly longer
    than the lease, and observing that the follower (a) transitioned to
    ``role == "leader"`` and (b) appended a new ``tick_commit`` row with its
    own relay_id.
    """

    def test_follower_promotes_within_lease_on_leader_stop(
        self,
        shared_broker_path: Path,
        shared_sensorium_ledger_path: Path,
    ) -> None:
        broker_a = _make_broker(shared_broker_path)
        broker_b = _make_broker(shared_broker_path)

        async def _drive() -> None:
            shell_a = _make_shell(
                broker_a,
                worker_id="worker-a",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )
            shell_b = _make_shell(
                broker_b,
                worker_id="worker-b",
                sensorium_ledger_path=shared_sensorium_ledger_path,
                tick_cadence_s=0.05,
            )
            shell_a.initial_seed()
            shell_b.initial_seed()
            leader, follower = (
                (shell_a, shell_b)
                if shell_a.role == "leader"
                else (shell_b, shell_a)
            )

            task_leader = asyncio.create_task(leader.run())
            task_follower = asyncio.create_task(follower.run())
            try:
                await asyncio.sleep(0.15)

                leader_relay_id_before = {
                    row["relay_id"] for row in _read_tick_commits(
                        shared_sensorium_ledger_path
                    )
                }
                assert len(leader_relay_id_before) == 1

                # Kill the leader. The leader's run-loop observes the stop
                # event, drops its Supervisor, and exits. Its lease remains
                # in the broker until expiry (~leader_lease_s from the last
                # renewal) — this is the lease-based election invariant.
                leader.stop()
                await asyncio.wait_for(task_leader, timeout=2.0)

                # Wait: lease (0.5s) + poll cadence (0.05s) + jitter.
                # Observing within a 1.5s budget gives generous headroom
                # on loaded CI hosts while still bounding the test.
                deadline = time.monotonic() + 1.5
                while time.monotonic() < deadline:
                    if follower.role == "leader":
                        break
                    await asyncio.sleep(0.05)
                assert follower.role == "leader", (
                    "follower never promoted within the lease budget"
                )

                # Give the new leader a tick or two to commit under its
                # own relay_id.
                await asyncio.sleep(0.2)
                rows_after = _read_tick_commits(shared_sensorium_ledger_path)
                new_relay_ids = {
                    row["relay_id"] for row in rows_after
                } - leader_relay_id_before
                assert new_relay_ids, (
                    "promoted follower did not commit any tick_commit row "
                    "under a new relay_id"
                )
            finally:
                follower.stop()
                await asyncio.wait_for(task_follower, timeout=2.0)

        try:
            asyncio.run(_drive())
        finally:
            broker_a.close()
            broker_b.close()


# --- Lifespan wiring sanity ----------------------------------------------


class TestLifespanBrokerWiring:
    """When ``XION_BROKER_DB_PATH`` is set, the lifespan builds a
    :class:`BrokerSupervisorShell` instead of a bare Supervisor, and
    :attr:`app.state.supervisor_shell` is non-None. When unset (default),
    the single-worker posture is preserved: ``app.state.broker`` is None
    and ``app.state.supervisor_shell`` is None."""

    def test_single_worker_posture_broker_none(
        self,
        app_factory,
    ) -> None:
        from fastapi.testclient import TestClient

        app = app_factory(tick_cadence_s=0.01)
        with TestClient(app):
            assert app.state.broker is None
            assert app.state.supervisor_shell is None

    def test_broker_env_wires_shell(
        self,
        app_factory,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        from fastapi.testclient import TestClient

        broker_path = tmp_path / "broker.sqlite3"
        monkeypatch.setenv("XION_BROKER_DB_PATH", str(broker_path))
        # Short lease so any leader-election side effects settle fast.
        monkeypatch.setenv("XION_BROKER_LEADER_LEASE_S", "1.0")
        monkeypatch.setenv("XION_BROKER_LEADER_RENEW_S", "0.2")

        app = app_factory(tick_cadence_s=0.05)
        with TestClient(app):
            assert app.state.broker is not None
            assert app.state.supervisor_shell is not None
            # The single lifespan owns a single shell; seed ran
            # synchronously, so the shell won the solo-claim election.
            assert app.state.supervisor_shell.role == "leader"
            # /drive serves non-None snapshot from the shell's
            # latest_snapshot() (which delegates to the internal Supervisor
            # while this shell is leader).
            snap = app.state.supervisor_shell.latest_snapshot()
            assert snap is not None

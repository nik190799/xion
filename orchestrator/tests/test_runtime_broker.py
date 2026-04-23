"""Tests for :mod:`orchestrator.runtime.broker` (Phase 5g+).

Coverage:

- Schema init (WAL mode pragma actually takes; three tables + index created)
- Snapshot round-trip (JSON round-trips exactly; INSERT OR REPLACE semantics)
- Leader election under two concurrent claimants (exactly one wins)
- Lease expiry + failover (follower promotes only after expiry)
- ``renew_leader`` refuses after lease expiry (no silent clobber)
- ``is_leader`` pure-read correctness across the lease lifecycle
- Rate-limit coherence under 1-, 2-, and 3-worker topologies
  (threaded simulation proves global budget coherence)
- WAL persistence across reopen (a closed + reopened broker sees prior state)
- ``BEGIN IMMEDIATE`` contention handling via busy_timeout (no split-brain)
- Factory :func:`load_broker_from_env` returns ``None`` when unset; parses
  overrides; raises on malformed inputs
- :class:`BrokerConfig` ``__post_init__`` rejects
  ``leader_renew_s >= leader_lease_s / 2``
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

import pytest

from orchestrator.runtime.broker import (
    Broker,
    BrokerConfig,
    BrokerError,
    RateCheck,
    SqliteBroker,
    load_broker_from_env,
)


# --- Fixtures ------------------------------------------------------------


@pytest.fixture()
def broker_path(tmp_path: Path) -> Path:
    """Return a fresh broker DB path under a pytest tmp dir."""
    return tmp_path / "broker.sqlite3"


@pytest.fixture()
def broker(broker_path: Path):
    """Construct a short-lease SqliteBroker for fast failover tests."""
    config = BrokerConfig(
        db_path=broker_path,
        leader_lease_s=0.5,
        leader_renew_s=0.1,
        busy_timeout_ms=5000,
    )
    b = SqliteBroker(config=config)
    try:
        yield b
    finally:
        b.close()


# --- BrokerConfig validation --------------------------------------------


class TestBrokerConfig:
    def test_accepts_valid_config(self, broker_path: Path) -> None:
        config = BrokerConfig(db_path=broker_path)
        assert config.leader_lease_s == 30.0
        assert config.leader_renew_s == 10.0
        assert config.busy_timeout_ms == 5000

    def test_rejects_renew_not_strictly_less_than_half_lease(
        self, broker_path: Path
    ) -> None:
        with pytest.raises(BrokerError, match="leader_renew_s"):
            BrokerConfig(
                db_path=broker_path,
                leader_lease_s=10.0,
                leader_renew_s=5.0,
            )
        with pytest.raises(BrokerError, match="leader_renew_s"):
            BrokerConfig(
                db_path=broker_path,
                leader_lease_s=10.0,
                leader_renew_s=6.0,
            )

    def test_rejects_non_positive_knobs(self, broker_path: Path) -> None:
        with pytest.raises(BrokerError, match="leader_lease_s"):
            BrokerConfig(db_path=broker_path, leader_lease_s=0.0)
        with pytest.raises(BrokerError, match="leader_renew_s"):
            BrokerConfig(db_path=broker_path, leader_renew_s=0.0)
        with pytest.raises(BrokerError, match="busy_timeout_ms"):
            BrokerConfig(db_path=broker_path, busy_timeout_ms=-1)

    def test_rejects_missing_parent_dir(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist" / "broker.sqlite3"
        with pytest.raises(BrokerError, match="parent directory does not exist"):
            BrokerConfig(db_path=missing)


# --- Schema init ---------------------------------------------------------


class TestSchemaInit:
    def test_tables_and_index_created(self, broker_path: Path) -> None:
        config = BrokerConfig(
            db_path=broker_path, leader_lease_s=1.0, leader_renew_s=0.1
        )
        b = SqliteBroker(config=config)
        try:
            rows = b._conn.execute(  # type: ignore[attr-defined]
                "SELECT name FROM sqlite_master WHERE type IN ('table','index') "
                "ORDER BY name"
            ).fetchall()
            names = {r[0] for r in rows}
            for required in (
                "supervisor_snapshot",
                "supervisor_leader",
                "rate_limit_events",
                "idx_rate_limit_events_principal_time",
            ):
                assert required in names
        finally:
            b.close()

    def test_wal_mode_active(self, broker_path: Path) -> None:
        config = BrokerConfig(
            db_path=broker_path, leader_lease_s=1.0, leader_renew_s=0.1
        )
        b = SqliteBroker(config=config)
        try:
            mode = b._conn.execute("PRAGMA journal_mode").fetchone()[0]  # type: ignore[attr-defined]
            assert mode.lower() == "wal"
        finally:
            b.close()

    def test_broker_satisfies_protocol(self, broker: SqliteBroker) -> None:
        # runtime_checkable Protocol — assert structural conformance.
        assert isinstance(broker, Broker)


# --- Snapshot round-trip -------------------------------------------------


class TestSnapshot:
    def test_latest_is_none_before_publish(self, broker: SqliteBroker) -> None:
        assert broker.latest_snapshot() is None

    def test_publish_then_read_round_trips(self, broker: SqliteBroker) -> None:
        snap = {
            "as_of_utc_ns": 1700000000000000000,
            "drive": {"mood": "steady", "energy": 0.72},
            "tick_count": 42,
        }
        broker.publish_snapshot(snap)
        got = broker.latest_snapshot()
        assert got == snap

    def test_publish_replaces_previous(self, broker: SqliteBroker) -> None:
        broker.publish_snapshot({"tick": 1})
        broker.publish_snapshot({"tick": 2})
        broker.publish_snapshot({"tick": 3})
        assert broker.latest_snapshot() == {"tick": 3}
        # Exactly one row lives in the table.
        rows = broker._conn.execute(  # type: ignore[attr-defined]
            "SELECT COUNT(*) FROM supervisor_snapshot"
        ).fetchone()
        assert rows[0] == 1

    def test_snapshot_survives_close_and_reopen(
        self, broker_path: Path
    ) -> None:
        config = BrokerConfig(
            db_path=broker_path, leader_lease_s=1.0, leader_renew_s=0.1
        )
        b1 = SqliteBroker(config=config)
        b1.publish_snapshot({"persistent": True, "n": 7})
        b1.close()
        b2 = SqliteBroker(config=config)
        try:
            assert b2.latest_snapshot() == {"persistent": True, "n": 7}
        finally:
            b2.close()


# --- Leader election -----------------------------------------------------


class TestLeaderElection:
    def test_first_acquire_wins(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        assert broker.is_leader("worker-a", now) is True

    def test_second_claimant_loses_while_lease_valid(
        self, broker: SqliteBroker
    ) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        # Immediately afterward, worker-b should be rejected.
        assert broker.try_acquire_leader("worker-b", now + 1) is False
        assert broker.is_leader("worker-a", now + 2) is True
        assert broker.is_leader("worker-b", now + 2) is False

    def test_reacquire_by_same_worker_is_renewal(
        self, broker: SqliteBroker
    ) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        later = now + int(0.1 * 1e9)
        assert broker.try_acquire_leader("worker-a", later) is True
        assert broker.is_leader("worker-a", later) is True

    def test_failover_after_lease_expiry(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        # Simulate clock advancing past lease (leader_lease_s = 0.5s).
        after_expiry = now + int(0.6 * 1e9)
        # At after_expiry, is_leader(worker-a) is False.
        assert broker.is_leader("worker-a", after_expiry) is False
        # Follower acquires.
        assert broker.try_acquire_leader("worker-b", after_expiry) is True
        assert broker.is_leader("worker-b", after_expiry) is True
        # Original leader can no longer claim to be leader at this time.
        assert broker.is_leader("worker-a", after_expiry) is False

    def test_renew_refuses_after_expiry(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        after_expiry = now + int(0.6 * 1e9)
        # A crashed-and-restarted worker-a that thinks it is still leader
        # cannot silently renew after its lease expired.
        assert broker.renew_leader("worker-a", after_expiry) is False

    def test_renew_succeeds_before_expiry(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        mid_lease = now + int(0.2 * 1e9)
        assert broker.renew_leader("worker-a", mid_lease) is True
        # After renewal, the lease extends by leader_lease_s again, so
        # the original-lease-expiry moment is now still within lease.
        original_expiry_moment = now + int(0.6 * 1e9)
        assert broker.is_leader("worker-a", original_expiry_moment) is True

    def test_renew_rejects_non_leader(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        assert broker.try_acquire_leader("worker-a", now) is True
        assert broker.renew_leader("worker-b", now + 1) is False

    def test_concurrent_acquire_exactly_one_wins(
        self, broker: SqliteBroker
    ) -> None:
        """Two threads hammer try_acquire_leader from a fresh state;
        exactly one must observe True."""
        winners: list[str] = []
        barrier = threading.Barrier(2)
        now = time.time_ns()

        def claim(worker: str) -> None:
            barrier.wait()
            if broker.try_acquire_leader(worker, now):
                winners.append(worker)

        t1 = threading.Thread(target=claim, args=("worker-a",))
        t2 = threading.Thread(target=claim, args=("worker-b",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        assert len(winners) == 1


# --- Rate-limit coherence ------------------------------------------------


class TestRateLimit:
    def test_under_budget_admits_and_records(self, broker: SqliteBroker) -> None:
        window_ns = int(60 * 1e9)
        result = broker.check_and_record_rate(
            "p1", window_ns, budget=3, now_ns=time.time_ns()
        )
        assert result.allowed is True
        assert result.retry_after_s == 0
        assert result.events_in_window == 1

    def test_at_budget_rejects(self, broker: SqliteBroker) -> None:
        window_ns = int(60 * 1e9)
        t0 = time.time_ns()
        # Consume full budget.
        for i in range(3):
            r = broker.check_and_record_rate(
                "p1", window_ns, budget=3, now_ns=t0 + i
            )
            assert r.allowed is True
        # Next call must reject.
        r = broker.check_and_record_rate("p1", window_ns, budget=3, now_ns=t0 + 3)
        assert r.allowed is False
        assert r.retry_after_s >= 1
        assert r.events_in_window == 3

    def test_eviction_frees_slot_after_window(self, broker: SqliteBroker) -> None:
        window_ns = int(1 * 1e9)  # 1-second window
        t0 = time.time_ns()
        for i in range(3):
            assert broker.check_and_record_rate(
                "p1", window_ns, budget=3, now_ns=t0 + i
            ).allowed
        # At t0 + window_ns + 3, cutoff is t0 + 3, so all three original
        # events (at t0, t0+1, t0+2) have evicted (delete uses <=; this
        # matches the Phase 5g-iv in-process SlidingWindow semantics).
        r = broker.check_and_record_rate(
            "p1", window_ns, budget=3, now_ns=t0 + window_ns + 3
        )
        assert r.allowed is True
        assert r.events_in_window == 1

    def test_per_principal_isolation(self, broker: SqliteBroker) -> None:
        window_ns = int(60 * 1e9)
        t0 = time.time_ns()
        for i in range(3):
            assert broker.check_and_record_rate(
                "alice", window_ns, budget=3, now_ns=t0 + i
            ).allowed
        # Alice is saturated.
        assert not broker.check_and_record_rate(
            "alice", window_ns, budget=3, now_ns=t0 + 3
        ).allowed
        # Bob is unaffected.
        assert broker.check_and_record_rate(
            "bob", window_ns, budget=3, now_ns=t0 + 4
        ).allowed

    def test_multi_worker_global_coherence(self, broker_path: Path) -> None:
        """Three 'worker' connections share one broker DB. A principal
        hitting all three workers in parallel exhausts exactly
        ``budget`` events globally, not ``N × budget``. This is the
        exact KW-RATE-001 pay-down property."""
        config = BrokerConfig(
            db_path=broker_path,
            leader_lease_s=10.0,
            leader_renew_s=1.0,
        )
        brokers = [SqliteBroker(config=config) for _ in range(3)]
        try:
            window_ns = int(60 * 1e9)
            budget = 10
            admitted: list[bool] = []
            lock = threading.Lock()
            t0 = time.time_ns()

            def hammer(b: SqliteBroker, worker_idx: int) -> None:
                for i in range(10):
                    # Strictly-increasing now_ns so SQLite orders the
                    # transactions deterministically; the test's
                    # correctness property (total admitted == budget)
                    # is independent of any ordering.
                    ts = t0 + worker_idx * 1000 + i * 100
                    r = b.check_and_record_rate("shared", window_ns, budget, ts)
                    with lock:
                        admitted.append(r.allowed)

            threads = [
                threading.Thread(target=hammer, args=(brokers[i], i))
                for i in range(3)
            ]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            # 30 total attempts; exactly budget admitted.
            assert len(admitted) == 30
            assert sum(1 for a in admitted if a) == budget
        finally:
            for b in brokers:
                b.close()

    def test_validates_inputs(self, broker: SqliteBroker) -> None:
        now = time.time_ns()
        with pytest.raises(BrokerError, match="principal_id"):
            broker.check_and_record_rate("", int(1e9), 1, now)
        with pytest.raises(BrokerError, match="window_ns"):
            broker.check_and_record_rate("p1", 0, 1, now)
        with pytest.raises(BrokerError, match="budget"):
            broker.check_and_record_rate("p1", int(1e9), 0, now)


# --- Factory -------------------------------------------------------------


class TestLoadBrokerFromEnv:
    def test_returns_none_when_unset(self) -> None:
        assert load_broker_from_env(env={}) is None
        assert load_broker_from_env(env={"XION_BROKER_DB_PATH": ""}) is None
        assert load_broker_from_env(env={"XION_BROKER_DB_PATH": "   "}) is None

    def test_constructs_broker_when_set(self, tmp_path: Path) -> None:
        db_path = tmp_path / "broker.sqlite3"
        env = {
            "XION_BROKER_DB_PATH": str(db_path),
            "XION_BROKER_LEADER_LEASE_S": "20.0",
            "XION_BROKER_LEADER_RENEW_S": "5.0",
            "XION_BROKER_BUSY_TIMEOUT_MS": "3000",
        }
        b = load_broker_from_env(env=env)
        try:
            assert isinstance(b, SqliteBroker)
            assert b.config.leader_lease_s == 20.0
            assert b.config.leader_renew_s == 5.0
            assert b.config.busy_timeout_ms == 3000
            assert db_path.exists()
        finally:
            assert b is not None
            b.close()

    def test_raises_on_malformed_float(self, tmp_path: Path) -> None:
        db_path = tmp_path / "broker.sqlite3"
        env = {
            "XION_BROKER_DB_PATH": str(db_path),
            "XION_BROKER_LEADER_LEASE_S": "not-a-float",
        }
        with pytest.raises(BrokerError, match="LEADER_LEASE_S"):
            load_broker_from_env(env=env)

    def test_raises_on_malformed_int(self, tmp_path: Path) -> None:
        db_path = tmp_path / "broker.sqlite3"
        env = {
            "XION_BROKER_DB_PATH": str(db_path),
            "XION_BROKER_BUSY_TIMEOUT_MS": "not-an-int",
        }
        with pytest.raises(BrokerError, match="BUSY_TIMEOUT_MS"):
            load_broker_from_env(env=env)


# --- Close semantics -----------------------------------------------------


class TestClose:
    def test_use_after_close_raises(self, broker_path: Path) -> None:
        config = BrokerConfig(
            db_path=broker_path, leader_lease_s=1.0, leader_renew_s=0.1
        )
        b = SqliteBroker(config=config)
        b.close()
        with pytest.raises(BrokerError, match="closed"):
            b.publish_snapshot({"tick": 1})

    def test_close_is_idempotent(self, broker_path: Path) -> None:
        config = BrokerConfig(
            db_path=broker_path, leader_lease_s=1.0, leader_renew_s=0.1
        )
        b = SqliteBroker(config=config)
        b.close()
        b.close()  # no-op, no exception

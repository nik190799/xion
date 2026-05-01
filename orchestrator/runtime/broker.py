"""Phase 5g+: the SQLite-WAL shared-state broker.

Doctrine anchors:
    docs/04-ARCHITECTURE.md § "Multi-worker coherence (Phase 5g+)"
    docs/33-MULTI-WORKER.md

This module owns three load-bearing things:

1. :class:`BrokerConfig` — the frozen, hash-friendly dataclass that captures
   the broker-file path and the lease cadence knobs. Loaded exactly once at
   lifespan startup and stashed on ``app.state.broker_config``.

2. :class:`Broker` Protocol — the Phase-6-replaceable surface. Six methods:
   ``publish_snapshot``, ``latest_snapshot``, ``try_acquire_leader``,
   ``renew_leader``, ``is_leader``, ``check_and_record_rate``. A Phase-6+
   ``AoMailboxBroker`` implementation honors the same Protocol; the
   factory below dispatches on env.

3. :class:`SqliteBroker` — the concrete Phase-5g+ implementation. One
   ``sqlite3.Connection`` per worker (``check_same_thread=False``) + an
   internal ``threading.Lock`` (SQLite-WAL allows concurrent readers but
   serializes writers; the lock prevents stdlib re-entry corruption
   across asyncio coroutines sharing the same connection).

The broker is optional — :func:`load_broker_from_env` returns ``None`` when
``XION_BROKER_DB_PATH`` is unset, and the existing single-worker posture
(Phase 5g-iv / 5g-v / 5g-ii) continues unchanged.

What this module deliberately does NOT do:

  - No cross-host coordination. The SQLite file is single-machine by design.
  - No distributed transaction semantics. The broker serves a narrow set of
    operations; it is not a general-purpose distributed database.
  - No broker-side authn. The DB file is on the orchestrator's trusted
    filesystem alongside every ledger; a malicious operator with write
    access can corrupt every ledger directly already.
  - No closure of KW-SUPERVISOR-002 (tick_commit heartbeat continuity
    across deploys); that closure needs a deploy-event ledger row the
    orchestrator does not yet publish.
"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

# --- Errors --------------------------------------------------------------


class BrokerError(RuntimeError):
    """Raised on broker-specific misconfiguration or unrecoverable I/O."""


# --- Config --------------------------------------------------------------


@dataclass(frozen=True)
class BrokerConfig:
    """Immutable broker configuration.

    Attributes:
        db_path: Path to the SQLite broker file. Parent directory must
            exist and be writable. The file itself is created on first
            open if absent.
        leader_lease_s: Supervisor leader lease TTL, in seconds. A
            crashed leader is replaced within at most this many seconds.
        leader_renew_s: Leader lease renewal cadence, in seconds. Must
            be strictly less than ``leader_lease_s / 2`` — a single
            missed renewal must not cause a spurious failover.
        busy_timeout_ms: SQLite ``PRAGMA busy_timeout`` value. The
            window during which a ``BEGIN IMMEDIATE`` transaction
            busy-waits for a contended page lock before failing with
            ``SQLITE_BUSY``. 5000ms is the doctrine default.
    """

    db_path: Path
    leader_lease_s: float = 30.0
    leader_renew_s: float = 10.0
    busy_timeout_ms: int = 5000

    def __post_init__(self) -> None:
        if self.leader_lease_s <= 0:
            raise BrokerError(
                f"leader_lease_s must be > 0; got {self.leader_lease_s}"
            )
        if self.leader_renew_s <= 0:
            raise BrokerError(
                f"leader_renew_s must be > 0; got {self.leader_renew_s}"
            )
        if self.leader_renew_s >= self.leader_lease_s / 2:
            raise BrokerError(
                "leader_renew_s must be strictly less than leader_lease_s / 2 "
                "(a single missed renewal must not cause a spurious failover); "
                f"got leader_renew_s={self.leader_renew_s} "
                f"leader_lease_s={self.leader_lease_s}"
            )
        if self.busy_timeout_ms < 0:
            raise BrokerError(
                f"busy_timeout_ms must be ≥ 0; got {self.busy_timeout_ms}"
            )
        parent = self.db_path.parent
        if not parent.exists():
            raise BrokerError(
                f"broker db_path parent directory does not exist: {parent} "
                "(operator must mkdir -p the parent; the broker creates the "
                "file, not the directory tree)"
            )
        if not parent.is_dir():
            raise BrokerError(
                f"broker db_path parent is not a directory: {parent}"
            )


# --- Rate-check result ---------------------------------------------------


@dataclass(frozen=True)
class RateCheck:
    """Outcome of a :meth:`Broker.check_and_record_rate` call.

    Attributes:
        allowed: ``True`` when the event was recorded and the principal
            is under budget; ``False`` when the budget was full and the
            event was NOT recorded (rate limiting is fail-closed).
        retry_after_s: Integer seconds until a budget slot frees. ``0``
            when ``allowed=True``; ``>= 1`` when ``allowed=False``.
        events_in_window: Count of recorded events in the window
            AFTER this call (so a successful record shows ``N+1`` and a
            rejected request shows the saturated ``budget``).
    """

    allowed: bool
    retry_after_s: int
    events_in_window: int


# --- Protocol ------------------------------------------------------------


@runtime_checkable
class Broker(Protocol):
    """The Phase-6-replaceable shared-state broker surface.

    A Phase-6+ AO-Core mailbox implementation will honor this Protocol;
    call-sites do not need to change when the mechanism swaps. See
    [`docs/33-MULTI-WORKER.md`](../../docs/33-MULTI-WORKER.md)
    § "Phase-6 replacement contract".
    """

    def publish_snapshot(self, snap: Mapping[str, Any]) -> None:
        """Atomically replace the single stored snapshot.

        The snapshot is the leader's most recent ``Supervisor.tick_once()``
        output (or any serializable mapping). Must be JSON-encodable with
        ``json.dumps(..., default=str)``.
        """

    def latest_snapshot(self) -> Mapping[str, Any] | None:
        """Return the most recently published snapshot, or ``None``.

        ``None`` means the broker has been opened but no snapshot has
        been published yet — the caller should treat it the same as the
        pre-boot "no Supervisor tick yet" state.
        """

    def try_acquire_leader(self, worker_id: str, now_ns: int) -> bool:
        """Attempt atomic lease acquisition. Returns ``True`` on win.

        Serialized by SQLite's page-level locking (``BEGIN IMMEDIATE``);
        two concurrent callers cannot both observe "lease expired" and
        both succeed. A successful acquire sets ``lease_expires_at_ns =
        now_ns + leader_lease_s * 1e9``.
        """

    def renew_leader(self, worker_id: str, now_ns: int) -> bool:
        """Extend the lease. Returns ``True`` only if ``worker_id``
        currently holds a still-valid lease (i.e., ``worker_id`` matches
        AND the lease has not yet expired).

        A ``False`` return means the caller has been silently demoted
        (either because the lease expired before renewal, or because
        another worker won the election). The caller must stop acting
        as leader when this returns ``False``.
        """

    def is_leader(self, worker_id: str, now_ns: int) -> bool:
        """Return ``True`` iff ``worker_id`` currently holds a still-
        valid lease. Pure read; does not mutate the lease record.
        """

    def check_and_record_rate(
        self,
        principal_id: str,
        window_ns: int,
        budget: int,
        now_ns: int,
    ) -> RateCheck:
        """Atomic per-principal sliding-window check + record.

        Runs in a single ``BEGIN IMMEDIATE`` transaction: delete events
        older than ``now_ns - window_ns``, count remaining, conditionally
        insert the new event if under ``budget``, commit. Two workers
        racing on the same principal cannot both observe "under budget"
        and both succeed.
        """

    def close(self) -> None:
        """Release any underlying resources (connections, locks). Safe to
        call multiple times. The broker must not be used after ``close()``.
        """


# --- SqliteBroker --------------------------------------------------------


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS supervisor_snapshot (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    json_blob       TEXT    NOT NULL,
    updated_at_ns   INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS supervisor_leader (
    singleton_id            INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    worker_id               TEXT    NOT NULL,
    lease_expires_at_ns     INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS rate_limit_events (
    principal_id    TEXT    NOT NULL,
    event_at_ns     INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_events_principal_time
    ON rate_limit_events (principal_id, event_at_ns);
"""


@dataclass
class SqliteBroker:
    """Concrete ``Broker`` implementation backed by a SQLite-WAL file.

    Opens a single :class:`sqlite3.Connection` per worker with
    ``check_same_thread=False`` so asyncio coroutines on different
    threads can share it, plus an internal :class:`threading.Lock` so
    the stdlib connection object is not re-entered concurrently.
    SQLite-WAL allows concurrent *readers* across connections; within
    a single connection the lock makes serialized access safe. The
    broker creates one connection per worker process; many workers
    across processes share the DB file via OS-level locking that WAL
    mode manages correctly.
    """

    config: BrokerConfig
    _conn: sqlite3.Connection = field(init=False, repr=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _closed: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self._conn = sqlite3.connect(
            str(self.config.db_path),
            check_same_thread=False,
            isolation_level=None,
            timeout=self.config.busy_timeout_ms / 1000.0,
        )
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute(
                f"PRAGMA busy_timeout={int(self.config.busy_timeout_ms)}"
            )
            self._conn.executescript(_SCHEMA_SQL)

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            try:
                self._conn.close()
            finally:
                self._closed = True

    def _ensure_open(self) -> None:
        if self._closed:
            raise BrokerError("broker has been closed; no further calls permitted")

    # --- Snapshot store --------------------------------------------------

    def publish_snapshot(self, snap: Mapping[str, Any]) -> None:
        self._ensure_open()
        blob = json.dumps(dict(snap), default=str, sort_keys=True)
        import time

        updated_at_ns = time.time_ns()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO supervisor_snapshot "
                "(id, json_blob, updated_at_ns) VALUES (1, ?, ?)",
                (blob, updated_at_ns),
            )

    def latest_snapshot(self) -> Mapping[str, Any] | None:
        self._ensure_open()
        with self._lock:
            row = self._conn.execute(
                "SELECT json_blob FROM supervisor_snapshot WHERE id = 1"
            ).fetchone()
        if row is None:
            return None
        return json.loads(row[0])

    # --- Leader election -------------------------------------------------

    def _lease_ns(self) -> int:
        return int(self.config.leader_lease_s * 1_000_000_000)

    def try_acquire_leader(self, worker_id: str, now_ns: int) -> bool:
        self._ensure_open()
        if not worker_id:
            raise BrokerError("worker_id must be non-empty")
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                row = cur.execute(
                    "SELECT worker_id, lease_expires_at_ns "
                    "FROM supervisor_leader WHERE singleton_id = 1"
                ).fetchone()
                if row is not None:
                    existing_worker, existing_expiry = row
                    if existing_worker == worker_id:
                        # Re-acquire our own lease — treat as renewal
                        # to keep the semantics clean for callers that
                        # restart and re-probe.
                        new_expiry = now_ns + self._lease_ns()
                        cur.execute(
                            "UPDATE supervisor_leader "
                            "SET lease_expires_at_ns = ? WHERE singleton_id = 1",
                            (new_expiry,),
                        )
                        cur.execute("COMMIT")
                        return True
                    if existing_expiry > now_ns:
                        # Another worker holds a still-valid lease.
                        cur.execute("ROLLBACK")
                        return False
                    # Lease expired; current worker wins.
                    cur.execute(
                        "UPDATE supervisor_leader "
                        "SET worker_id = ?, lease_expires_at_ns = ? "
                        "WHERE singleton_id = 1",
                        (worker_id, now_ns + self._lease_ns()),
                    )
                else:
                    cur.execute(
                        "INSERT INTO supervisor_leader "
                        "(singleton_id, worker_id, lease_expires_at_ns) "
                        "VALUES (1, ?, ?)",
                        (worker_id, now_ns + self._lease_ns()),
                    )
                cur.execute("COMMIT")
                return True
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def renew_leader(self, worker_id: str, now_ns: int) -> bool:
        self._ensure_open()
        if not worker_id:
            raise BrokerError("worker_id must be non-empty")
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                row = cur.execute(
                    "SELECT worker_id, lease_expires_at_ns "
                    "FROM supervisor_leader WHERE singleton_id = 1"
                ).fetchone()
                if row is None:
                    cur.execute("ROLLBACK")
                    return False
                existing_worker, existing_expiry = row
                if existing_worker != worker_id:
                    cur.execute("ROLLBACK")
                    return False
                if existing_expiry <= now_ns:
                    # Our lease has expired; we must re-acquire, not
                    # silently renew. A crashed-and-restarted worker
                    # that thinks it is still the leader but whose
                    # lease expired cannot clobber a newly elected one.
                    cur.execute("ROLLBACK")
                    return False
                cur.execute(
                    "UPDATE supervisor_leader "
                    "SET lease_expires_at_ns = ? WHERE singleton_id = 1",
                    (now_ns + self._lease_ns(),),
                )
                cur.execute("COMMIT")
                return True
            except Exception:
                cur.execute("ROLLBACK")
                raise

    def is_leader(self, worker_id: str, now_ns: int) -> bool:
        self._ensure_open()
        with self._lock:
            row = self._conn.execute(
                "SELECT worker_id, lease_expires_at_ns "
                "FROM supervisor_leader WHERE singleton_id = 1"
            ).fetchone()
        if row is None:
            return False
        existing_worker, existing_expiry = row
        return existing_worker == worker_id and existing_expiry > now_ns

    # --- Rate limiter ----------------------------------------------------

    def check_and_record_rate(
        self,
        principal_id: str,
        window_ns: int,
        budget: int,
        now_ns: int,
    ) -> RateCheck:
        self._ensure_open()
        if not principal_id:
            raise BrokerError("principal_id must be non-empty")
        if window_ns < 1:
            raise BrokerError(f"window_ns must be ≥ 1; got {window_ns}")
        if budget < 1:
            raise BrokerError(f"budget must be ≥ 1; got {budget}")
        cutoff_ns = now_ns - window_ns
        with self._lock:
            cur = self._conn.cursor()
            cur.execute("BEGIN IMMEDIATE")
            try:
                cur.execute(
                    "DELETE FROM rate_limit_events "
                    "WHERE principal_id = ? AND event_at_ns <= ?",
                    (principal_id, cutoff_ns),
                )
                count_row = cur.execute(
                    "SELECT COUNT(*) FROM rate_limit_events "
                    "WHERE principal_id = ?",
                    (principal_id,),
                ).fetchone()
                current = int(count_row[0]) if count_row else 0
                if current < budget:
                    cur.execute(
                        "INSERT INTO rate_limit_events "
                        "(principal_id, event_at_ns) VALUES (?, ?)",
                        (principal_id, now_ns),
                    )
                    cur.execute("COMMIT")
                    return RateCheck(
                        allowed=True,
                        retry_after_s=0,
                        events_in_window=current + 1,
                    )
                # Full bucket. retry_after = (oldest + window) - now.
                oldest_row = cur.execute(
                    "SELECT MIN(event_at_ns) FROM rate_limit_events "
                    "WHERE principal_id = ?",
                    (principal_id,),
                ).fetchone()
                cur.execute("COMMIT")
                oldest_ns = (
                    int(oldest_row[0]) if oldest_row and oldest_row[0] is not None else now_ns
                )
                retry_after_ns = (oldest_ns + window_ns) - now_ns
                retry_after_s = _ns_to_ceil_seconds(retry_after_ns)
                return RateCheck(
                    allowed=False,
                    retry_after_s=max(1, retry_after_s),
                    events_in_window=current,
                )
            except Exception:
                cur.execute("ROLLBACK")
                raise


def _ns_to_ceil_seconds(ns: int) -> int:
    """Round nanoseconds up to the next whole second. Always ≥ 0."""
    if ns <= 0:
        return 0
    return (ns + 999_999_999) // 1_000_000_000


# --- Factory -------------------------------------------------------------


def load_broker_from_env(env: Mapping[str, str] | None = None) -> Broker | None:
    """Return a :class:`Broker` constructed from environment, or ``None``.

    Recognized env vars:

    - ``XION_BROKER_DB_PATH`` — path to the SQLite broker file. When unset
      or empty, this returns ``None`` (the single-worker posture stays
      backward-compatible). The parent dir must exist.
    - ``XION_BROKER_LEADER_LEASE_S`` — override the leader lease TTL
      (float seconds; default 30.0).
    - ``XION_BROKER_LEADER_RENEW_S`` — override the leader renewal
      cadence (float seconds; default 10.0).
    - ``XION_BROKER_BUSY_TIMEOUT_MS`` — override the SQLite busy_timeout
      (integer milliseconds; default 5000).

    Parameters:
        env: An optional environment mapping for testing. Defaults to
            :data:`os.environ`.

    Returns:
        A :class:`SqliteBroker` when configured; ``None`` when the
        operator has not opted in to multi-worker coherence.
    """
    e = env if env is not None else os.environ
    raw = e.get("XION_BROKER_DB_PATH", "").strip()
    if not raw:
        return None
    db_path = Path(raw).expanduser().resolve()
    kwargs: dict[str, Any] = {"db_path": db_path}
    lease_raw = e.get("XION_BROKER_LEADER_LEASE_S", "").strip()
    if lease_raw:
        try:
            kwargs["leader_lease_s"] = float(lease_raw)
        except ValueError as exc:
            raise BrokerError(
                f"XION_BROKER_LEADER_LEASE_S must be a float; got {lease_raw!r}"
            ) from exc
    renew_raw = e.get("XION_BROKER_LEADER_RENEW_S", "").strip()
    if renew_raw:
        try:
            kwargs["leader_renew_s"] = float(renew_raw)
        except ValueError as exc:
            raise BrokerError(
                f"XION_BROKER_LEADER_RENEW_S must be a float; got {renew_raw!r}"
            ) from exc
    busy_raw = e.get("XION_BROKER_BUSY_TIMEOUT_MS", "").strip()
    if busy_raw:
        try:
            kwargs["busy_timeout_ms"] = int(busy_raw)
        except ValueError as exc:
            raise BrokerError(
                f"XION_BROKER_BUSY_TIMEOUT_MS must be an integer; got {busy_raw!r}"
            ) from exc
    config = BrokerConfig(**kwargs)
    return SqliteBroker(config=config)

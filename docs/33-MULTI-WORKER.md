# 33 — Multi-Worker Coherence (SQLite-WAL broker behind the `Broker` Protocol)

> *Phase 5g-iv shipped an admission gate the operator could only run one worker behind. Phase 5g-ii made that worker stream. Phase 5g+ lets the operator run more than one — without `SENSORIUM_LEDGER` corruption, without rate-limit over-allocation, and without taking on an external dependency a solo builder cannot sustain.*

## What this document is (and is not)

This is the operational doctrine for the **Multi-Worker Coherence Surface** — the SQLite-in-WAL broker that Phase 5g+ ships at [`orchestrator/runtime/broker.py`](../orchestrator/runtime/broker.py), the lifespan wiring that promotes one uvicorn worker to the Supervisor leader and demotes the rest to followers, the broker-backed rate-limit store that replaces `InProcessSlidingWindow` when a broker is configured, and the `Broker` Protocol surface that a Phase-6+ AO Core mailbox implementation will honor.

It is **not**:

- **A replacement for [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "Multi-worker coherence (Phase 5g+)".** That section pins the constitutional shape (the five properties, the explicit non-properties, the code-surface layout, the verification contract). This document pins the *operator workflow* — env knobs, backup/reset runbook, failure modes, observability. The architecture section is shorter and harder to amend; this document is longer and re-tunable.
- **A replacement for [`docs/30-API-ADMISSION.md`](./30-API-ADMISSION.md).** That document pins admission (bearer tokens, rate-limit shape, TLS). This document pins how the admission surface's rate-limit buckets become globally coherent across N workers when the broker is configured. The admission contract at the route level is unchanged.
- **A distributed-systems textbook.** SQLite-WAL is not a Raft cluster. It is a single-file coherence mechanism on a single host. Cross-host consensus is Phase 6+ AO Core territory and is not in scope here.
- **A cross-host coordination story.** The broker file is by design single-machine. A multi-host D2 deployment runs one broker per host; see § "What this doctrine deliberately does NOT promise" at the bottom.

## Why pin this now

Two linked Known Weaknesses tracked this from the moment the admission surface shipped:

1. **`KW-API-002` — Supervisor shares FastAPI event loop; single uvicorn worker only.** Two workers would each construct a Supervisor, each tick at the Genesis Default cadence, and each write `tick_commit` rows under a different `relay_id` to the same `SENSORIUM_LEDGER`, silently corrupting the cadence record and violating the implicit "one Supervisor per Core" property.
2. **`KW-RATE-001` — Per-principal sliding window is in-process; multi-worker deployment loses bucket coherence.** N workers run N independent Python processes, each with its own `app.state.rate_limiters` map; the effective per-principal budget is `N × XION_API_RATE_BUDGET`. A principal targeting all N workers in parallel can consume N× the intended budget.

Both KWs named the same pay-down in prose: a multi-worker shared-state broker. Phase 5g+ is that broker, shipped in the smallest correct mechanism a solo builder can operate at 3am.

## Doctrine — why SQLite in WAL mode

Phase 5g+ had four candidate mechanisms. Three were rejected; one was picked.

**Option A — Redis pub/sub.** Correct mechanism for the publish-subscribe shape and for atomic rate-limit buckets (`INCR` + `EXPIRE`). *Rejected.* Adds a second service that has to be supervised, monitored, TLS-terminated, and persisted; a solo builder already has one orchestrator process to keep alive and one set of ledgers to back up. A Redis dependency would double the 3am surface for work a one-file SQLite broker handles on a single machine.

**Option B — AO Process mailbox on AO Core.** *Rejected for Phase 5g+; adopted as the Phase-6+ replacement.* The AO mailbox is the honest long-term home for Supervisor snapshot publication and cross-host coordination — it is on-chain, it is durable, it is substrate-resilient, and it is verifiable from off-host. The blocker is that AO Core does not exist yet at the Phase-5g+ horizon. When it does, the `Broker` Protocol shipped here is the exact seam an `AoMailboxBroker` slots into.

**Option C — In-house TCP-loopback daemon.** *Rejected.* A second process to supervise, a hand-rolled wire protocol, a second failure mode the operator has to monitor, and a second set of liveness probes — all for coherence work SQLite already solves. This would be "not-invented-here" energy applied to a problem the stdlib ships a solution for.

**Option D — SQLite in WAL mode at a configurable path (picked).** Pure stdlib (`sqlite3` ships with Python), reliable on Windows (where `KW-API-002` explicitly named filesystem pub/sub quirks as the reason *not* to roll our own — SQLite's cross-platform file-locking is the reason it ships the way it does), kill-safe (no second process to supervise), inspectable with `sqlite3 <path>` at 3am, one file to back up, one file to nuke and re-create. The `Broker` Protocol interface is narrow enough that Phase-6 AO Process mailbox replaces it behind the same surface.

## Broker schema

The broker is a single SQLite file at `XION_BROKER_DB_PATH`. On first open (or re-open with a different schema version in a future phase), the broker runs `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=5000`, then `CREATE TABLE IF NOT EXISTS` for three tables.

### `supervisor_snapshot` — one-row snapshot store

```sql
CREATE TABLE supervisor_snapshot (
    id              INTEGER PRIMARY KEY CHECK (id = 1),
    json_blob       TEXT    NOT NULL,
    updated_at_ns   INTEGER NOT NULL
);
```

Always exactly zero or one row. The leader writes it via `INSERT OR REPLACE` after each `Supervisor.tick_once()`; followers read the latest row via `SELECT`. The `CHECK (id = 1)` constraint prevents a coding bug from accidentally writing multiple rows.

### `supervisor_leader` — one-row lease

```sql
CREATE TABLE supervisor_leader (
    singleton_id            INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    worker_id               TEXT    NOT NULL,
    lease_expires_at_ns     INTEGER NOT NULL
);
```

Always exactly zero or one row. Lease acquisition runs in a `BEGIN IMMEDIATE` transaction: if the existing row's `lease_expires_at_ns < now_ns` (or no row exists), `INSERT OR REPLACE` with `worker_id = <this worker>` and `lease_expires_at_ns = now_ns + leader_lease_s * 1e9`; otherwise the existing lease still holds and the call returns `False`. Renewal (`renew_leader`) only succeeds when the current row's `worker_id` matches the caller AND the existing lease has not yet expired — a crashed-and-restarted worker that thinks it is still the leader but whose lease expired cannot silently clobber a newly elected leader.

### `rate_limit_events` — append-and-prune events

```sql
CREATE TABLE rate_limit_events (
    principal_id    TEXT    NOT NULL,
    event_at_ns     INTEGER NOT NULL
);
CREATE INDEX idx_rate_limit_events_principal_time
    ON rate_limit_events (principal_id, event_at_ns);
```

Each `check_and_record_rate(principal_id, window_ns, budget, now_ns)` call runs in a single `BEGIN IMMEDIATE` transaction: `DELETE WHERE principal_id = ? AND event_at_ns < now_ns - window_ns`, `SELECT COUNT(*) WHERE principal_id = ?`, conditional `INSERT` (only when count < budget), commit, return `RateCheck(allowed, retry_after_s, events_in_window)`. The transaction is serialized by SQLite's page-level locking; two workers racing on the same principal cannot both observe "under budget" and both succeed. The `retry_after_s` is computed from the oldest event in the window at `now_ns - window_ns` rollover — same semantics as the Phase-5g-iv in-process sliding window.

Prune policy: the delete runs on every `check_and_record_rate` call, so the table size is bounded by `budget * active_principals`. For Genesis Default (60 events / 60 s per principal) with 10 active principals that is 600 rows — not enough to merit a separate VACUUM strategy. When a future Phase raises `XION_API_RATE_BUDGET` above `10^4` or opens the surface to thousands of concurrent principals, a `PRAGMA incremental_vacuum` strategy lands alongside that phase.

## Lease semantics

The Genesis Defaults for lease cadence are:

- `leader_lease_s = 30.0` — the lease TTL. A crashed leader is replaced within at most this many seconds.
- `leader_renew_s = 10.0` — the renewal cadence. The leader re-writes its lease every 10 seconds. The `BrokerConfig.__post_init__` refuses to construct a config where `leader_renew_s >= leader_lease_s / 2`; a single missed renewal must not cause a spurious failover.

The failover sequence under a leader crash:

```
t=0.0     Leader (pid 1) acquires lease, lease_expires_at_ns = t + 30s.
t=10.0    Leader renews, lease_expires_at_ns = t + 30s.
t=20.0    Leader renews, lease_expires_at_ns = t + 30s.
t=25.0    Leader crashes (SIGKILL, OOM, host reboot, anything).
t=25..50  Followers poll try_acquire_leader on each own tick cadence or on
          each incoming GET /drive. All calls return False because the lease
          has not yet expired (CHECK lease_expires_at_ns > now_ns).
t=50.0    First follower whose try_acquire_leader runs after the lease has
          expired wins the election. BEGIN IMMEDIATE serializes the race
          across every follower; exactly one worker wins. That worker becomes
          the new leader and starts ticking the Supervisor.
```

The `tick_commit` row stream in `SENSORIUM_LEDGER` therefore shows:
- One `relay_id` from t=0 to t=25 (the original leader's pid, possibly prefixed with a relay-name suffix).
- A gap from t=25 to (at most) t=50.
- A new `relay_id` starting at t=50.

`xion-verify supervisor-singleton` recognizes this pattern as a valid failover transition (bounded by `leader_lease_s + leader_renew_s` slack) and does not flag it as corruption. Two `relay_id`s emitting `tick_commit` rows at the same wall-clock second is the corruption pattern the verifier flags.

## SQLite-WAL posture

`PRAGMA journal_mode=WAL` is the central setting. Without it, SQLite uses the rollback journal, which serializes *every* access (readers block writers, writers block readers, all with file-level locking). WAL mode allows concurrent readers alongside one writer, serializes writers via a write-ahead log, and flushes the log to the main database on checkpoint (every ~1000 pages by default).

Concrete implications for the operator:

- **`XION_BROKER_DB_PATH` names one file.** But the on-disk footprint is three files: `<name>`, `<name>-wal`, `<name>-shm`. Do not back up only the main file during an active connection — the WAL holds committed-but-not-yet-checkpointed transactions. Either stop the orchestrator before copying the main file, or copy all three files atomically, or use the `sqlite3` `.backup` command which handles WAL correctly.
- **`PRAGMA synchronous=NORMAL`** (not `FULL`) is the trade-off. At `NORMAL`, a committed transaction survives any application crash but may be lost if the host power-cycles with the WAL still in kernel buffers. For a single-machine orchestrator whose ledgers are the source of truth and whose broker state is recoverable from ledger replay, the few-milliseconds saving per commit is worth the narrow window of loss. An operator who prefers the stricter posture can override via `PRAGMA synchronous=FULL` at broker construction — the trade-off is a measurable per-commit latency increase.
- **`PRAGMA busy_timeout=5000`** (5 seconds) is the serialization safety net. If two workers issue concurrent `BEGIN IMMEDIATE` transactions on the same page, the loser busy-waits for up to 5s before failing with `SQLITE_BUSY`. For the broker's workloads (snapshot publish + leader renew + rate-limit check) this window is orders of magnitude larger than typical contention. A `SQLITE_BUSY` from the broker is a signal of a much deeper problem (the DB is on a failed disk, another process is holding the file open for minutes) and the caller surfaces it honestly rather than retrying.

## Operator env surface

Two new env knobs, both additive:

| Var | Default | Meaning |
|-----|---------|---------|
| `XION_BROKER_DB_PATH` | unset | Path to the SQLite broker file. When unset, the broker is disabled and the orchestrator runs in the single-worker posture exactly as 5g-iv shipped it (full backward compatibility). When set, the parent dir must exist and be writable; the lifespan creates or opens the file on boot. |
| `XION_API_WORKERS` | `1` | The number of uvicorn workers the launcher passes via `uvicorn.run(..., workers=N)`. When `>1`, `XION_BROKER_DB_PATH` must also be set; the launcher fails closed at boot otherwise. |

The launcher's fail-closed check is deliberate: `workers>1` without a broker is the exact corruption path `KW-API-002` and `KW-RATE-001` named, and shipping a launcher that allowed it silently would be dishonest. The error message names both env knobs and points at this document.

## Operator runbook — first multi-worker boot

```bash
# Pick a broker-file location. One file; any writable path works.
export XION_BROKER_DB_PATH="/var/lib/xion/broker.sqlite3"
mkdir -p "$(dirname "$XION_BROKER_DB_PATH")"

# Pick the worker count. 2 is a reasonable starting point on commodity
# hardware; 4 is the usual ceiling before the per-worker overhead outweighs
# the parallelism gain at the /chat surface's latency profile.
export XION_API_WORKERS=2

# Launch as usual.
python -m orchestrator.api
```

On first boot, the orchestrator creates the broker file, each worker opens it, one worker wins the leader lease, and the other becomes a follower. Inspect:

```bash
# Confirm WAL mode is active.
sqlite3 "$XION_BROKER_DB_PATH" "PRAGMA journal_mode;"
# Expected: wal

# Inspect the current leader.
sqlite3 "$XION_BROKER_DB_PATH" "SELECT worker_id, lease_expires_at_ns FROM supervisor_leader;"

# Inspect the latest snapshot (just the keys).
sqlite3 "$XION_BROKER_DB_PATH" "SELECT json_extract(json_blob, '$.as_of_utc_ns'), json_extract(json_blob, '$.drive.mood') FROM supervisor_snapshot;"
```

`xion-verify supervisor-singleton` can be run against the `SENSORIUM_LEDGER` to confirm the broker is producing the expected `tick_commit` shape:

```bash
xion-verify supervisor-singleton --window-s 3600
# Expected: PASS — single dominant relay_id over the last hour, no overlaps.
```

## Operator runbook — backup, reset, migrate

- **Backup.** Either `sqlite3 "$XION_BROKER_DB_PATH" ".backup /path/to/broker.backup.sqlite3"` (online, safe during live traffic) or stop the orchestrator and copy all three files (`<name>`, `<name>-wal`, `<name>-shm`) atomically. The broker holds no irreplaceable state — the Supervisor snapshot is rebuilt from ticks, the leader lease is rebuilt on next boot, and the rate-limit events are transient — so a lost broker file is an operational inconvenience, not a doctrinal emergency.
- **Reset.** To clear all broker state (expire all leases, drop all rate-limit buckets, nuke the snapshot), stop the orchestrator and `rm -f "$XION_BROKER_DB_PATH"{,-wal,-shm}`. On next boot the broker re-creates the schema from scratch. This is a safe operation; it does not touch any ledger.
- **Migrate to Phase-6 AO mailbox (future).** When the Phase-6+ AO Core mailbox lands, a new env knob (tentative name `XION_BROKER_AO_PROCESS_ID`) points the broker factory at an `AoMailboxBroker` implementation honoring the same `Broker` Protocol. Migration is: stop, switch env, start. The SQLite file can be deleted after a successful AO-mailbox cutover; no data migration is needed because the broker holds only recoverable state.

## Failure modes and the honest responses

| Symptom | Probable cause | Honest response |
|---------|---------------|-----------------|
| Launcher refuses to boot with "`XION_API_WORKERS > 1` but `XION_BROKER_DB_PATH` is not set" | Operator asked for multi-worker without a broker | Set `XION_BROKER_DB_PATH` or revert to `XION_API_WORKERS=1`. There is no flag to bypass this check; the fail-closed is load-bearing. |
| Launcher refuses to boot with "broker DB parent dir does not exist" | Path typo or missing parent dir | `mkdir -p "$(dirname "$XION_BROKER_DB_PATH")"`. The broker does not create arbitrary parent paths; it creates the file, not the directory tree. |
| `SENSORIUM_LEDGER` shows two `relay_id`s in the same tick cadence band | Broker-disabled multi-worker deployment ran against the same ledger directory | This is the `KW-API-002` corruption pattern. Stop the orchestrator, confirm `XION_BROKER_DB_PATH` is set, confirm `XION_API_WORKERS > 1` only when the broker is set, restart. The corrupted `SENSORIUM_LEDGER` rows are structurally honest (each worker wrote its own view); operator post-hoc dedup is a forensic task, not a recovery task. |
| `xion-verify supervisor-singleton` reports FAIL | Either the broker is configured but not wired correctly, or two brokers on the same ledger dir | Inspect `supervisor_leader` in the broker file; confirm only one `worker_id` is currently leasing; confirm `XION_BROKER_DB_PATH` points at the same file for every worker. |
| A principal is hitting a higher effective rate budget than configured | Broker-backed rate-limit store is not configured despite `XION_API_WORKERS > 1` | The launcher should have refused to boot in this state; if it did not, file a bug with the launcher log and revert to single-worker until fixed. |
| `sqlite3.OperationalError: database is locked` surfacing into the API | Broker file is on a filesystem that does not support proper file-locking (some NFS / CIFS mounts) | Move the broker file to a local filesystem. SQLite's lock semantics assume POSIX file locking; networked filesystems often ship broken implementations. This is a SQLite limitation, not an orchestrator bug. |

## Observability

The broker exposes its state through the DB file itself — any operator with `sqlite3` on their path can read it. The orchestrator does not add broker metrics to the `/sensorium` or `/drive` surfaces at 5g+; those surfaces remain Supervisor-facing, not broker-facing. A future `GET /broker/status` surface is a Phase-6+ feature that lands alongside the AO-mailbox migration — at that point the broker becomes a first-class presence in the protocol, not an implementation detail behind the Supervisor.

## Verification — `xion-verify supervisor-singleton`

See [`docs/04-ARCHITECTURE.md`](./04-ARCHITECTURE.md) § "Multi-worker coherence (Phase 5g+)" for the three properties (S1 dominant `relay_id`, S2 monotonic timestamps per epoch, S3 no overlapping cadence bands). Returns `NOT_YET_SEALED` when no broker is configured in the observed environment — a single-worker deployment trivially satisfies the singleton property, and the verifier reports that honestly rather than issue a fake green.

The verifier lives at [`xion-verify/src/xion_verify/commands/supervisor_singleton.py`](../xion-verify/src/xion_verify/commands/supervisor_singleton.py). Its test suite at [`xion-verify/tests/test_supervisor_singleton.py`](../xion-verify/tests/test_supervisor_singleton.py) covers: clean single-leader ledgers, clean failover ledgers (bounded transitions), corrupted ledgers (two `relay_id`s ticking concurrently — FAIL), and `NOT_YET_SEALED` for pre-broker ledgers.

## Phase-6 replacement contract

The `Broker` Protocol (six methods) is the stable surface. A Phase-6+ `AoMailboxBroker` implementation:

1. Implements `publish_snapshot` by posting an AO message to a dedicated `xion_supervisor` process.
2. Implements `latest_snapshot` by reading that process's state (or its most recent message).
3. Implements `try_acquire_leader` / `renew_leader` / `is_leader` against a deterministic on-chain lease record maintained by the same process.
4. Implements `check_and_record_rate` against a rate-limit process that serializes the same `DELETE / SELECT COUNT / INSERT` semantics via AO message-order.
5. Ships behind a new env knob (`XION_BROKER_AO_PROCESS_ID`) that `load_broker_from_env` dispatches on, preserving the SQLite path for operators who want local-only coherence.

Call-sites do not change. `orchestrator/api/lifespan.py` constructs whatever broker the factory returns; `orchestrator/api/admission.py` uses whatever `RateLimitStore` the lifespan builds; `orchestrator/supervisor.py` calls whatever `publish` hook the lifespan passes. This is the shape-symmetric replacement posture `verify_bearer` already carries for the `KW-AUTH-001` federated-identity work.

## What this doctrine deliberately does NOT promise

- **No cross-host coordination.** Single-machine by design. A multi-host D2 deployment runs one broker per host and accepts that each host's Supervisor is its own leader over its own subset of Relay authority. Cross-host consensus is Phase 6+ AO Core.
- **No distributed transaction semantics.** The broker provides serialized access to a small number of narrow operations. It is not a general-purpose distributed database, a queue, or a pub/sub bus. Adding those would widen the Protocol into territory AO Core is the right long-term home for.
- **No broker-side authn.** The DB file sits on the orchestrator's trusted filesystem alongside every ledger. A malicious operator with write access to the working directory can already corrupt every ledger directly; broker-side authn would be security theater at that threat level.
- **No closure of `KW-SUPERVISOR-002`.** That KW (tick_commit heartbeat continuity across deploys) needs a deploy-event ledger row the orchestrator does not yet publish. Phase 5g+ closes only the two KWs the broker mechanism directly resolves.
- **No automatic SQLite VACUUM.** The prune-on-check-and-record policy keeps the `rate_limit_events` table bounded for Genesis-scale workloads. A future phase that opens the surface to thousands of concurrent principals ships a `PRAGMA incremental_vacuum` strategy alongside it.
- **No migration tool.** `XION_BROKER_DB_PATH` names one file; a Phase-6+ AO-mailbox cutover deletes the SQLite file after the switch. No data migration is needed because the broker holds only recoverable state.

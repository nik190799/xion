"""`xion-verify supervisor-singleton` — single-leader Supervisor property
over ``SENSORIUM_LEDGER.jsonl`` (Phase 5g+ landing, closes ``KW-API-002``).

Property promised.

  The Phase 5g+ broker-backed deployment commits that **exactly one
  Supervisor ticks at any given wall-clock instant**, regardless of how
  many uvicorn workers are running. In the single-worker posture the
  property is structurally satisfied (there is only one Supervisor to
  tick); in the multi-worker broker-backed posture the lease-based
  election at [`docs/33-MULTI-WORKER.md`](../../../docs/33-MULTI-WORKER.md)
  enforces it. This verifier walks the ``tick_commit`` stream and
  asserts the property after the fact.

Properties this verifier checks.

  A. **Single dominant leader.** The ``relay_id`` values across the
     observed window form a single dominant id with **bounded** failover
     transitions. A transition is a ``tick_commit`` row whose
     ``relay_id`` differs from the immediately prior row's. A transition
     bound of one per ``leader_lease_s`` is the Phase-5g+ promise;
     operators can loosen via ``--max-failovers`` when they know a
     deliberate restart cycle happened in the window.

  B. **Within-leader monotonicity.** Within one continuous leader epoch
     (a run of ``tick_commit`` rows with identical ``relay_id``), the
     ``as_of_utc_ns`` field is strictly monotonic. Non-monotonic ticks
     inside one epoch mean a single Supervisor's clock went backwards —
     a corruption signature of either a system NTP step during a tick
     or a second Supervisor instance that shared a ``relay_id`` (the
     worse failure mode).

  C. **No concurrent-leader time-range overlap.** For each distinct
     ``relay_id`` observed in the window, its ticks define a closed
     time range ``[min_as_of_utc_ns, max_as_of_utc_ns]``. No two
     distinct ``relay_id``s may have overlapping ranges: a leader that
     keeps ticking after a successor has promoted (or two Supervisors
     running concurrently on an mis-configured multi-worker deploy)
     will produce a strict overlap here — the precise corruption
     signature ``KW-API-002`` named.

Exit codes.

  OK (0)             Every property holds over the observed window.
  FAIL (1)           At least one property is violated. The error
                     message names the offending ``relay_id`` pair,
                     timestamps, and the violated property letter
                     (A / B / C).
  NOT_YET_SEALED (2) The SENSORIUM_LEDGER is missing, empty, or has no
                     ``tick_commit`` rows in the observed window. A
                     deployment has not yet ticked; verification is
                     vacuously satisfied but cannot demonstrate live
                     coverage.

What this verifier deliberately does NOT do.

  - Does not speak to the broker. The ``supervisor_leader`` table is a
    live-state datum; this verifier is ``xion-verify``'s post-hoc
    property checker (trust by structure, not by promise — the ledger
    is the source of truth, not the broker).
  - Does not distinguish broker-configured from single-worker ledgers.
    Both produce the same ``tick_commit`` shape; a single-worker ledger
    with one ``relay_id`` passes trivially. Operators who want to
    assert "the broker is actually configured" look at
    ``docs/33-MULTI-WORKER.md``'s runbook, not this verifier.
  - Does not enforce cadence compliance (that is ``KW-SUPERVISOR-002``,
    Phase 6+).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import click

from xion_verify.exit_codes import FAIL, NOT_YET_SEALED, OK
from xion_verify.repo import RepoRootNotFound, find_repo_root

_SENSORIUM_NAME = "SENSORIUM_LEDGER.jsonl"
_DEFAULT_WINDOW_HOURS = 24
_DEFAULT_MAX_FAILOVERS = 1  # One bounded failover per observed window.


def _default_sensorium_path(repo_root: Path) -> Path:
    env = os.environ.get("XION_SENSORIUM_LEDGER")
    return Path(env) if env else repo_root / _SENSORIUM_NAME


def _fail(message: str) -> None:
    click.echo(f"supervisor-singleton: FAIL: {message}", err=True)
    sys.exit(FAIL)


def _not_yet_sealed(message: str) -> None:
    click.echo(f"supervisor-singleton: NOT_YET_SEALED: {message}")
    sys.exit(NOT_YET_SEALED)


@click.command(
    name="supervisor-singleton",
    help=(
        "Walk SENSORIUM_LEDGER tick_commit rows; verify single-leader "
        "Supervisor property (Phase 5g+). Closes KW-API-002."
    ),
)
@click.option(
    "--path",
    "ledger_override",
    type=click.Path(path_type=Path),
    default=None,
    help=(
        "Override the SENSORIUM_LEDGER path (defaults to "
        "$XION_SENSORIUM_LEDGER then <repo>/SENSORIUM_LEDGER.jsonl)."
    ),
)
@click.option(
    "--window-hours",
    "window_hours",
    type=click.FloatRange(min=0.0, min_open=True),
    default=float(_DEFAULT_WINDOW_HOURS),
    show_default=True,
    help=(
        "Walk only tick_commit rows whose as_of_utc_ns falls within this "
        "many hours of 'now'. A 24h window matches the operator's default "
        "forensic horizon."
    ),
)
@click.option(
    "--max-failovers",
    "max_failovers",
    type=click.IntRange(min=0),
    default=_DEFAULT_MAX_FAILOVERS,
    show_default=True,
    help=(
        "Maximum allowed relay_id transitions inside the window. Default "
        "1 bounds one graceful failover per lease budget; operators who "
        "know the window contains a deliberate restart cycle raise this."
    ),
)
def supervisor_singleton(
    ledger_override: Path | None,
    window_hours: float,
    max_failovers: int,
) -> None:
    try:
        repo_root = find_repo_root()
    except RepoRootNotFound as exc:
        click.echo(f"supervisor-singleton: FAIL: {exc}", err=True)
        sys.exit(FAIL)

    try:
        from orchestrator.sensorium.ledger import iter_rows
    except ImportError as exc:
        _not_yet_sealed(
            "orchestrator.sensorium.ledger not importable "
            f"({type(exc).__name__}: {exc}); Phase 5c code surface not "
            "present on this fork."
        )

    path = (
        ledger_override
        if ledger_override is not None
        else _default_sensorium_path(repo_root)
    )

    if not path.is_file():
        _not_yet_sealed(
            f"no SENSORIUM_LEDGER at {path}. Supervisor has not emitted "
            "any tick_commit rows yet."
        )

    # Pull every tick_commit row inside the window.
    window_ns = int(window_hours * 60 * 60 * 1_000_000_000)
    import time as _time

    now_ns = _time.time_ns()
    cutoff_ns = now_ns - window_ns

    tick_rows: list[dict[str, Any]] = []
    for row in iter_rows(path):
        if row.get("event_type") != "tick_commit":
            continue
        as_of_ns = row.get("as_of_utc_ns")
        if as_of_ns is None or as_of_ns < cutoff_ns:
            continue
        tick_rows.append(row)

    if not tick_rows:
        _not_yet_sealed(
            f"no tick_commit rows in the last {window_hours}h at {path}. "
            "The Supervisor may not be running, or the window is smaller "
            "than the tick cadence."
        )

    # ----- Property A: single dominant leader, bounded failovers --------

    # The ledger's file order is the canonical insertion order (every
    # row is seq-chained with prev_hash/this_hash). Preserve that order
    # so a within-epoch clock regression in Property B actually shows
    # up; sorting by as_of_utc_ns would silently mask the very bug
    # Property B is there to catch.
    transitions: list[tuple[str, str, int, int]] = []  # (from, to, prev_ns, next_ns)
    for prev, curr in zip(tick_rows, tick_rows[1:]):
        prev_rid = str(prev["relay_id"])
        curr_rid = str(curr["relay_id"])
        if prev_rid != curr_rid:
            transitions.append(
                (
                    prev_rid,
                    curr_rid,
                    int(prev["as_of_utc_ns"]),
                    int(curr["as_of_utc_ns"]),
                )
            )

    if len(transitions) > max_failovers:
        transition_summary = "; ".join(
            f"{a}->{b} at {ns}" for a, b, _prev_ns, ns in transitions
        )
        _fail(
            f"Property A violated: {len(transitions)} relay_id transitions "
            f"in the last {window_hours}h (max allowed "
            f"{max_failovers}). Multiple Supervisors ticked concurrently "
            "or an unbounded churn is happening. Transitions: "
            f"{transition_summary}."
        )

    # ----- Property B: within-epoch monotonicity ------------------------

    # Group rows into contiguous runs of identical relay_id; assert
    # as_of_utc_ns strictly monotonic inside each.
    epoch_start_idx = 0
    for i in range(1, len(tick_rows)):
        if tick_rows[i]["relay_id"] == tick_rows[i - 1]["relay_id"]:
            if (
                int(tick_rows[i]["as_of_utc_ns"])
                <= int(tick_rows[i - 1]["as_of_utc_ns"])
            ):
                _fail(
                    "Property B violated: within leader epoch "
                    f"relay_id={tick_rows[i]['relay_id']!r}, "
                    f"as_of_utc_ns={tick_rows[i]['as_of_utc_ns']} is not "
                    f"strictly greater than prior "
                    f"as_of_utc_ns={tick_rows[i - 1]['as_of_utc_ns']}. "
                    "Either the Supervisor's clock went backwards or two "
                    "Supervisors share a relay_id (corruption signature "
                    "KW-API-002 named)."
                )
        else:
            epoch_start_idx = i

    # ----- Property C: no concurrent-leader time-range overlap ----------

    # For each distinct relay_id, compute [min, max] of its tick
    # as_of_utc_ns. Any two distinct ranges that overlap signal
    # concurrent leaders — the KW-API-002 corruption signature.
    ranges: dict[str, tuple[int, int]] = {}
    for row in tick_rows:
        rid = str(row["relay_id"])
        ns = int(row["as_of_utc_ns"])
        if rid in ranges:
            lo, hi = ranges[rid]
            ranges[rid] = (min(lo, ns), max(hi, ns))
        else:
            ranges[rid] = (ns, ns)

    rids_ordered = sorted(ranges.keys(), key=lambda r: ranges[r][0])
    for i in range(len(rids_ordered)):
        for j in range(i + 1, len(rids_ordered)):
            rid_a = rids_ordered[i]
            rid_b = rids_ordered[j]
            lo_a, hi_a = ranges[rid_a]
            lo_b, hi_b = ranges[rid_b]
            # Overlap iff lo_b <= hi_a (given lo_a <= lo_b by sort).
            if lo_b <= hi_a:
                _fail(
                    "Property C violated: concurrent-leader overlap — "
                    f"relay_id={rid_a!r} range [{lo_a}, {hi_a}] "
                    f"overlaps relay_id={rid_b!r} range [{lo_b}, {hi_b}]. "
                    "Two Supervisors ticked during the same wall-clock "
                    "interval (the KW-API-002 corruption signature)."
                )

    # ----- Success reporting -------------------------------------------

    unique_rids = sorted({str(r["relay_id"]) for r in tick_rows})
    click.echo(
        f"supervisor-singleton: OK (ticks={len(tick_rows)} "
        f"window_hours={window_hours} "
        f"unique_relay_ids={unique_rids} "
        f"failovers={len(transitions)}/{max_failovers} path={path})"
    )
    sys.exit(OK)

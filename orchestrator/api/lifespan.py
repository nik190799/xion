"""FastAPI lifespan context manager for the Phase 5f HTTP surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The HTTP Surface
(Phase 5f)" — the "Lifespan contract (doctrinal)" subsection.

This module owns the Supervisor's lifecycle: construction, the
load-bearing synchronous pre-seed tick, the Relay wire-up, the
background run() task, and the shutdown + timeout + hard-cancel
dance. No HTTP handler code lives here; no routes are registered
here. The lifespan is the only place where Supervisor and Relay are
joined into a single coherent runtime.

Why a synchronous pre-seed tick before ``yield``:
  The doctrine promises ``GET /drive`` and ``GET /sensorium`` never
  return a 503-warming-up response. The only way to keep that promise
  is to make sure ``latest_snapshot()`` is non-``None`` before the
  FastAPI app accepts its first request. ``tick_once()`` is cheap
  (one dict copy + one JSON append) and blocking in startup is the
  textbook FastAPI pattern for this exact case.

Why a timeout + hard-cancel on shutdown:
  If ``tick_once()`` is stuck inside the run loop (disk full, I/O
  hung, event-loop deadlock), the Supervisor's cooperative
  ``stop()`` signal will never be observed. We bound teardown time
  to ``2 * tick_cadence_s`` and then cancel the task. The cancel is
  Python-exception-clean (``asyncio.CancelledError``), so whatever
  Supervisor was doing at cancel time will unwind through its
  normal ``finally`` clauses; any in-flight ledger write completes
  or raises cleanly by virtue of the stdlib's ``open`` / ``write``
  atomicity, not by our own effort.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from orchestrator.supervisor import Supervisor


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Construct the Supervisor, pre-seed it, wire it into the Relay,
    schedule its run loop, yield for request handling, then tear it
    down on shutdown.
    """
    deps = app.state.deps

    supervisor = Supervisor(
        relay=deps.relay,
        tick_cadence_s=deps.tick_cadence_s,
        sensorium_ledger_path=deps.sensorium_ledger_path,
    )

    # Doctrine pin: pre-seed the snapshot synchronously. After this
    # returns, ``supervisor.latest_snapshot()`` is non-None and the
    # first SENSORIUM_LEDGER tick_commit row is on disk. A pre-seed
    # failure (disk full, permission error) propagates out of the
    # lifespan and FastAPI refuses to start the app — which is the
    # correct behaviour, because a process that cannot write its
    # first tick has no business serving /sensorium or /drive.
    supervisor.tick_once()

    # Wire the Supervisor into the Relay AFTER the pre-seed tick, so
    # any in-process code that races the lifespan cannot observe a
    # sensorium_source whose latest_snapshot is still None. The private
    # attribute write is intentional: the Relay's public __init__
    # accepts sensorium_source at construction time, but the lifespan
    # constructs the Supervisor after the Relay — a post-construction
    # setter would be public API clutter for the one caller that needs
    # it. If a second caller appears, promote this to a Relay method.
    deps.relay._sensorium_source = supervisor

    # Schedule the run loop. asyncio.create_task requires a running
    # event loop; FastAPI's lifespan runs inside one, so this is safe.
    supervisor_task = asyncio.create_task(
        supervisor.run(),
        name="xion-supervisor-run",
    )

    app.state.supervisor = supervisor
    app.state.supervisor_task = supervisor_task

    try:
        yield
    finally:
        supervisor.stop()

        # Shutdown budget: 2 * tick_cadence_s. Generous — a healthy
        # Supervisor exits on the next poll boundary (<= poll_interval_s,
        # ~0.1s at default cadence). The 2x margin covers a tick_once()
        # call in flight (I/O bound by a slow disk) plus the poll.
        shutdown_timeout_s = max(1.0, 2.0 * supervisor._tick_cadence_s)

        try:
            await asyncio.wait_for(supervisor_task, timeout=shutdown_timeout_s)
        except TimeoutError:
            # Hard-cancel. Await once more so the cancellation is
            # observed and exceptions drain; suppress CancelledError
            # (that is what we asked for) and re-raise anything else.
            supervisor_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await supervisor_task

        # Drop the wire-up so a subsequent lifespan (unusual, but
        # possible in test re-runs on the same Relay instance) does
        # not observe a stale Supervisor.
        deps.relay._sensorium_source = None


__all__ = ["lifespan"]

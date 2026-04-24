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
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from orchestrator.billing import (
    ChainBroken as PaymentChainBroken,
)
from orchestrator.billing import (
    load_billing_config_from_env,
)
from orchestrator.billing import (
    verify_chain as verify_payment_chain,
)
from orchestrator.cognition.soul_prompt import (
    SoulPromptHashMismatchError,
    load_soul_prompt,
)
from orchestrator.inference_router import (
    DEFAULT_POLICY_MODE,
    InferenceRouter,
    PolicyMode,
    default_manifest_path,
)
from orchestrator.runtime import (
    BrokerSupervisorShell,
    default_worker_id,
    load_broker_from_env,
)
from orchestrator.supervisor import Supervisor

from .admission import (
    build_rate_limiters,
    load_admission_config_from_env,
)
from .pricing import load_pricing_config_from_env


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Construct the Supervisor, pre-seed it, wire it into the Relay,
    schedule its run loop, yield for request handling, then tear it
    down on shutdown.
    """
    deps = app.state.deps

    # --- Phase 5g+: load shared-state broker (optional) ---------------
    # When XION_BROKER_DB_PATH is unset, the broker is disabled and the
    # orchestrator runs in the single-worker posture exactly as
    # Phase 5g-iv / 5g-v / 5g-ii shipped it (full backward compat).
    # When set, the launcher will have ensured this worker is one of
    # XION_API_WORKERS processes sharing the broker, and this lifespan
    # instance elects itself leader or follower via the broker.
    broker = None
    broker_renew_s = 10.0
    if getattr(deps, "broker", None) is not None:
        broker = deps.broker
        broker_renew_s = getattr(deps, "broker_leader_renew_s", 10.0)
    else:
        broker = load_broker_from_env()
        if broker is not None:
            # Pull the renew cadence off the broker's config for the
            # shell's renewal loop.
            from orchestrator.runtime import SqliteBroker as _SqliteBroker

            if isinstance(broker, _SqliteBroker):
                broker_renew_s = broker.config.leader_renew_s
    app.state.broker = broker

    if broker is None:
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
        app.state.supervisor_shell = None
    else:
        # Broker-backed posture. Build the shell, attempt leader
        # election, pre-seed if we win. Followers do not pre-seed
        # (they read the leader's published snapshot on the first
        # /drive / /sensorium request).
        shell = BrokerSupervisorShell(
            broker=broker,
            worker_id=default_worker_id(),
            leader_renew_s=broker_renew_s,
            supervisor_factory=Supervisor,
            sensorium_ledger_path=deps.sensorium_ledger_path,
            tick_cadence_s=deps.tick_cadence_s,
            relay=deps.relay,
        )
        shell.initial_seed()
        supervisor = shell  # type: ignore[assignment]
        app.state.supervisor_shell = shell

    # --- Phase 5g-i: load .env, register providers, bootstrap -------
    # Runs AFTER the Supervisor pre-seed so a failed floor does not
    # delay Sensorium snapshot publication (the read-only surface is
    # observable even when Xion cannot speak). Runs BEFORE the Relay
    # wire-up and run-task schedule so /chat has a definitive
    # no_floor / router state by the time any request arrives.

    # An explicitly-supplied router is treated as fully configured;
    # the env loader + env-driven provider registration is skipped.
    # Tests rely on this to keep themselves hermetic from the operator
    # shell's environment (and from any live Ollama / OpenRouter endpoint).
    if deps.router is not None:
        router = deps.router
    else:
        _load_dotenv_if_present()
        router = _build_router_from_env()
        _register_env_providers(router)

    app.state.router = router
    app.state.no_floor = False
    app.state.no_floor_reason = ""
    app.state.no_floor_manifest_id = ""

    try:
        router.bootstrap()
    except Exception as e:
        app.state.no_floor = True
        app.state.no_floor_reason = str(e)
        ids = sorted(router.active_open_weights_ids())
        app.state.no_floor_manifest_id = ",".join(ids) if ids else "(none pinned)"
        print(
            "State-of-Xion: Inference Router bootstrap refused. "
            f"{e} "
            "Chat surface is serving 503 open_weights_floor_unsatisfied; "
            "read-only surface (/health, /drive, /sensorium) remains available.",
            file=sys.stderr,
            flush=True,
        )

    # --- Phase 5g-i.1: load Soul Prompt ----------------------------
    try:
        app.state.soul_prompt = load_soul_prompt()
    except SoulPromptHashMismatchError as e:
        print(
            f"State-of-Xion: Soul Prompt refused load. {e} "
            "Refusing to start. See genesis/SOUL.md § 0.",
            file=sys.stderr,
            flush=True,
        )
        raise

    # --- Phase 5g-iii: load posted-pricing config ------------------
    # Runs BEFORE the Relay wire-up so a misconfigured pricing split
    # fails-closed at startup (the app refuses to serve ANY endpoint,
    # not just /pricing — a doctrine-violating price is a constitutional
    # violation, not a soft warning). An explicitly-supplied config on
    # ``deps.pricing_config`` wins over the env loader; tests use this
    # to keep their pricing config hermetic.
    if getattr(deps, "pricing_config", None) is not None:
        app.state.pricing_config = deps.pricing_config
    else:
        app.state.pricing_config = load_pricing_config_from_env()

    # --- Phase 5g-iii: load billing config + verify PAYMENT_LEDGER chain
    # Doctrine pin (docs/04-ARCHITECTURE.md § "Lifespan contract"):
    # a corrupt PAYMENT_LEDGER is a constitutional failure, not a
    # warning; the app refuses to register /chat if the existing
    # ledger file's chain is broken. Explicitly-supplied configs on
    # ``deps.billing_config`` win over the env loader (test seam).
    if getattr(deps, "billing_config", None) is not None:
        app.state.billing_config = deps.billing_config
    else:
        app.state.billing_config = load_billing_config_from_env()

    try:
        verify_payment_chain(app.state.billing_config.payment_ledger_path)
    except PaymentChainBroken as e:
        raise PaymentChainBroken(
            "PAYMENT_LEDGER chain broken at startup; refusing to start. "
            f"Detail: {e}"
        ) from e

    # --- Phase 5g-iv: load admission config + build rate limiters ---
    # Doctrine pin (docs/04-ARCHITECTURE.md § "The Admission-Control
    # Surface (Phase 5g-iv)" → "Lifespan contract"): a misconfigured
    # admission table (short token, malformed principal_id, non-loopback
    # bind without TLS) is a constitutional failure, not a warning.
    # The app refuses to register any route if the admission config
    # does not load. Explicitly-supplied configs on
    # ``deps.admission_config`` win over the env loader (test seam).
    if getattr(deps, "admission_config", None) is not None:
        admission_config = deps.admission_config
    else:
        admission_config = load_admission_config_from_env()
    app.state.admission_config = admission_config
    # Phase 5g+ rate-limit broker wiring. When the broker is configured
    # (XION_BROKER_DB_PATH set), ``build_rate_limiters`` returns a
    # BrokerBackedSlidingWindowStore so all N workers see one global
    # per-principal bucket. When unset, it returns the Phase 5g-iv
    # in-process sliding-window store (backward-compat; KW-RATE-001 is
    # the in-process residual when no broker is configured).
    app.state.rate_limiters = build_rate_limiters(
        admission_config, broker=broker
    )
    # The /health per-IP bucket map is built lazily on first request;
    # initialise the slot so admission_dependency does not have to
    # check for its existence on every call.
    app.state.health_rate_limiters = {}

    # Wire the Supervisor (or broker shell) into the Relay AFTER the
    # pre-seed tick, so any in-process code that races the lifespan
    # cannot observe a sensorium_source whose latest_snapshot is still
    # None. The private attribute write is intentional: the Relay's
    # public __init__ accepts sensorium_source at construction time,
    # but the lifespan constructs the Supervisor after the Relay — a
    # post-construction setter would be public API clutter for the one
    # caller that needs it. If a second caller appears, promote this
    # to a Relay method.
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

        # Close the broker if we own it. The shell's run loop has
        # already stopped by this point; closing the broker after the
        # shell is safe (no in-flight writes).
        if app.state.broker is not None:
            with contextlib.suppress(Exception):
                app.state.broker.close()
            app.state.broker = None


def _load_dotenv_if_present() -> None:
    """Best-effort loader for a repo-root ``.env`` file.

    Intentionally tiny: stdlib only, no ``python-dotenv``. Already-set
    environment variables WIN (do not overwrite). Missing file is not
    an error. Malformed lines are skipped silently; a malformed .env
    is an operator-surface problem, not a runtime one.

    Lines honoured:
        KEY=value
        KEY="value with spaces"
        KEY='value'
    Comments start with ``#``. Blank lines are skipped.
    """
    # Repo root is the directory containing genesis/; search upward
    # from cwd. On failure (e.g., operator runs elsewhere), we just
    # skip — environment may already be set by the process manager.
    candidate: Path | None = None
    for base in [Path.cwd(), *Path.cwd().parents]:
        if (base / ".env").is_file():
            candidate = base / ".env"
            break
    if candidate is None:
        return

    try:
        text = candidate.read_text(encoding="utf-8")
    except OSError:
        return

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        os.environ[key] = value


def _build_router_from_env() -> InferenceRouter:
    """Construct an ``InferenceRouter`` with the manifest + policy mode
    the environment dictates. Providers are registered separately
    by ``_register_env_providers``.
    """
    policy_env = os.environ.get("XION_INFERENCE_POLICY", "").strip().lower()
    mode: PolicyMode
    if policy_env == "open_weights_only":
        mode = "open_weights_only"
    elif policy_env in ("", "hosted_api_first"):
        mode = DEFAULT_POLICY_MODE
    else:
        print(
            f"State-of-Xion: unrecognised XION_INFERENCE_POLICY={policy_env!r}; "
            f"falling back to Genesis Default {DEFAULT_POLICY_MODE!r}.",
            file=sys.stderr,
            flush=True,
        )
        mode = DEFAULT_POLICY_MODE
    return InferenceRouter(
        manifest_path=default_manifest_path(),
        policy_mode=mode,
    )


def _register_env_providers(router: InferenceRouter) -> None:
    """Register OpenRouter (if XION_OPENROUTER_API_KEY set) and Ollama
    (always).

    Failures in provider construction (e.g., malformed URL) are
    surfaced to stderr but do NOT crash the lifespan — a missing or
    broken provider just goes un-registered, and the Router's
    subsequent ``bootstrap()`` decides whether that still satisfies
    Invariant 17.
    """
    # Import lazily so the Phase 5f read-only surface does not pull
    # the providers package during module load.
    from orchestrator.inference_router.providers import (
        OllamaGenerativeProvider,
        OpenRouterGenerativeProvider,
    )
    from orchestrator.inference_router.providers.ollama import (
        OllamaProviderError,
    )
    from orchestrator.inference_router.providers.openrouter import (
        OpenRouterProviderError,
    )

    if os.environ.get("XION_OPENROUTER_API_KEY", "").strip():
        try:
            openrouter = OpenRouterGenerativeProvider()
        except OpenRouterProviderError as e:
            print(
                f"State-of-Xion: OpenRouter provider not registered: {e}",
                file=sys.stderr,
                flush=True,
            )
        else:
            router.register(openrouter)

    try:
        ollama = OllamaGenerativeProvider()
    except OllamaProviderError as e:
        print(
            f"State-of-Xion: Ollama provider not registered: {e}",
            file=sys.stderr,
            flush=True,
        )
    else:
        router.register(ollama)


__all__ = ["lifespan"]

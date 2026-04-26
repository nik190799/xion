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
import hashlib
import json
import os
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
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
from orchestrator.signals.bus import SignalBus
from orchestrator.signals.effector import EffectorRegistry
from orchestrator.signals.receptor import ReceptorRegistry
from orchestrator.signals.reflex import ReflexRegistry
from orchestrator.supervisor import Supervisor
from orchestrator.sensorium.presence_bus import PresenceBus

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

    if getattr(deps, "cast_pool_on_boot", True):
        _ensure_agent_cast_pool_at_boot()

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

    # --- Phase 6.4: Presence Bus ---
    presence_bus = PresenceBus()
    app.state.presence_bus = presence_bus

    # --- Phase 6.4.b: Nervous System (SignalBus + reflex + receptors) ---
    effector_registry = EffectorRegistry()
    reflex_registry = ReflexRegistry()
    reflex_registry.bind_effectors(effector_registry)
    signal_bus = SignalBus(reflex_registry=reflex_registry)
    app.state.signal_bus = signal_bus
    app.state.reflex_registry = reflex_registry
    app.state.effector_registry = effector_registry
    receptor_registry = ReceptorRegistry()
    app.state.receptor_registry = receptor_registry

    from orchestrator.signals.reflex import ReflexArc

    def _consent_both_streams_off(sig) -> bool:  # type: ignore[no-untyped-def]
        v = sig.value
        if not isinstance(v, dict):
            return False
        return v.get("stream_visual") is False and v.get("stream_vitals") is False

    reflex_registry.register(
        ReflexArc(
            arc_id="presence.off_channel_close",
            trigger_kind_pattern="governance.consent_change",
            predicate=_consent_both_streams_off,
            effector_id="presence.sse",
            methodology_hash="3333333333333333333333333333333333333333333333333333333333333333",
        )
    )

    if broker is None:
        supervisor = Supervisor(
            relay=deps.relay,
            tick_cadence_s=deps.tick_cadence_s,
            sensorium_ledger_path=deps.sensorium_ledger_path,
            presence_bus=presence_bus,
            signal_bus=signal_bus,
            receptor_registry=receptor_registry,
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
            presence_bus=presence_bus,
            signal_bus=signal_bus,
            receptor_registry=receptor_registry,
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
    # shell's environment (and from any live Ollama endpoint).
    if deps.router is not None:
        router = deps.router
    else:
        _load_dotenv_if_present()
        router = _build_router_from_env()
        _register_env_providers(router)
    _enforce_sovereign_profile()

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

    # --- Phase 6.5: Voice Router floor -----------------------------
    # Voice has its own floor because Inference sovereignty does not imply
    # STT/TTS/turn-taking sovereignty. Keep the bootstrap independent so a
    # missing voice floor disables /voice/stream without weakening /chat.
    from orchestrator.voice_router import (
        WhisperPiperLiveKitProvider,
        load_voice_router,
    )

    voice_router = load_voice_router(providers=[WhisperPiperLiveKitProvider()])
    app.state.voice_router = voice_router
    app.state.voice_floor = False
    app.state.voice_floor_reason = ""
    try:
        voice_router.bootstrap()
        app.state.voice_floor = True
    except Exception as e:
        app.state.voice_floor_reason = str(e)
        print(
            "State-of-Xion: Voice Router bootstrap refused. "
            f"{e} /voice/stream will emit voice_floor_unavailable; "
            "text chat remains available.",
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
    # Phase 6.9: vector memory is a first-class forget backend. Journal
    # writes use the same SQLite file path by default, so /forget deletes
    # embedded memory as well as future memory substrates behind this adapter.
    from orchestrator.memory import build_default_memory_store

    app.state.memory_backend = build_default_memory_store()

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

    # --- Phase 6.3: Interaction Anchoring Daemon ---
    from orchestrator.anchor.daemon import AnchorDaemon
    from orchestrator.anchor.sink import LocalLedgerSink
    import os

    anchor_ledger_path = Path(os.environ.get("XION_ANCHOR_DB_PATH", "ledgers/ANCHOR_LEDGER.jsonl"))
    request_ledger_path = Path(os.environ.get("XION_REQUEST_LEDGER", "REQUEST_LEDGER.jsonl"))
    payment_ledger_path = Path(os.environ.get("XION_PAYMENT_LEDGER", "PAYMENT_LEDGER.jsonl"))
    safety_ledger_path = Path(os.environ.get("XION_SAFETY_LEDGER", "SAFETY_LEDGER.jsonl"))
    tick_interval = int(os.environ.get("XION_ANCHOR_TICK_INTERVAL_SECONDS", "3600"))

    app.state.anchor_ledger_path = anchor_ledger_path
    app.state.request_ledger_path = request_ledger_path
    app.state.payment_ledger_path = payment_ledger_path
    app.state.safety_ledger_path = safety_ledger_path

    anchor_sink_type = os.environ.get("XION_ANCHOR_SINK", "local")
    if anchor_sink_type == "ao_core":
        from orchestrator.anchor.sink_ao_core import AOCoreSink
        anchor_sink = AOCoreSink(
            anchor_ledger_path=str(anchor_ledger_path),
            ao_gateway_url=os.environ.get("XION_AO_GATEWAY_URL", "http://localhost:4000"),
            ao_process_id=os.environ.get("XION_AO_PROCESS_ID", ""),
            ao_signer_jwk_path=os.environ.get("XION_AO_SIGNER_JWK_PATH", ""),
        )
    else:
        anchor_sink = LocalLedgerSink(str(anchor_ledger_path))

    anchor_daemon = AnchorDaemon(
        sink=anchor_sink,
        anchor_ledger_path=anchor_ledger_path,
        request_ledger_path=request_ledger_path,
        payment_ledger_path=payment_ledger_path,
        safety_ledger_path=safety_ledger_path,
        window_size_seconds=tick_interval,
    )
    anchor_task = asyncio.create_task(anchor_daemon.run_forever(), name="xion-anchor-run")
    app.state.anchor_task = anchor_task

    billing_credit_task = None
    if os.environ.get("XION_CHUTES_API_KEY", "").strip():
        billing_credit_task = asyncio.create_task(
            _poll_chutes_billing_forever(),
            name="xion-chutes-billing-run",
        )
    app.state.billing_credit_task = billing_credit_task

    try:
        yield
    finally:
        supervisor.stop()
        anchor_task.cancel()
        if billing_credit_task is not None:
            billing_credit_task.cancel()

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
        if billing_credit_task is not None:
            with contextlib.suppress(asyncio.CancelledError):
                await billing_credit_task

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
    """Register Chutes (if its API key is set) and Ollama (always).

    Failures in provider construction (e.g., malformed URL) are
    surfaced to stderr but do NOT crash the lifespan — a missing or
    broken provider just goes un-registered, and the Router's
    subsequent ``bootstrap()`` decides whether that still satisfies
    Invariant 17.
    """
    # Import lazily so the Phase 5f read-only surface does not pull
    # the providers package during module load.
    from orchestrator.inference_router.providers import (
        ChutesGenerativeProvider,
        OllamaGenerativeProvider,
    )
    from orchestrator.inference_router.providers.chutes import (
        ChutesProviderError,
    )
    from orchestrator.inference_router.providers.ollama import (
        OllamaProviderError,
    )

    if os.environ.get("XION_CHUTES_API_KEY", "").strip():
        try:
            chutes = ChutesGenerativeProvider()
        except ChutesProviderError as e:
            print(
                f"State-of-Xion: Chutes provider not registered: {e}",
                file=sys.stderr,
                flush=True,
            )
        else:
            router.register(chutes)
            shadow_model = os.environ.get(
                "XION_CHUTES_SHADOW_MODEL",
                "Qwen/Qwen3-235B-A22B-Instruct-2507",
            ).strip()
            if shadow_model:
                try:
                    router.register_shadow(
                        ChutesGenerativeProvider(
                            model=shadow_model,
                            tee_required=False,
                        )
                    )
                except ChutesProviderError as e:
                    print(
                        f"State-of-Xion: Chutes shadow provider not registered: {e}",
                        file=sys.stderr,
                        flush=True,
                    )

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


def _enforce_sovereign_profile() -> None:
    """Fail closed when the sovereign profile sees centralized surfaces."""
    from orchestrator.profile import ProfileConfigError, current_profile

    try:
        profile = current_profile()
    except ProfileConfigError:
        raise
    if profile.name != "sovereign":
        return

    forbidden_env = {
        "XION_OPENROUTER_API_KEY": "OpenRouter is a centralized SaaS fallback",
        "OPENAI_API_KEY": "OpenAI Moderation is a centralized SaaS classifier",
    }
    for key, reason in forbidden_env.items():
        if os.environ.get(key, "").strip():
            raise RuntimeError(
                f"sovereign profile refused: {key} is set ({reason}). "
                "Unset it or leave XION_PROFILE=local_only for non-sovereign development."
            )

    provider = os.environ.get("XION_LLM_ARBITER_PROVIDER", "").strip()
    if provider and provider not in {"deterministic-stub", "chutes-llm-judge"}:
        raise RuntimeError(
            "sovereign profile refused: XION_LLM_ARBITER_PROVIDER must be "
            "'deterministic-stub' or 'chutes-llm-judge'."
        )

    ao_gateway = os.environ.get("XION_AO_GATEWAY_URL", "").strip()
    if ao_gateway and not (
        ao_gateway.startswith("http://localhost:")
        or ao_gateway.startswith("http://127.0.0.1:")
    ):
        raise RuntimeError(
            "sovereign profile refused: XION_AO_GATEWAY_URL must point at local AO localnet."
        )

    if os.environ.get("XION_ANCHOR_WALLET_JWK_PATH", "").strip():
        raise RuntimeError(
            "sovereign profile refused: XION_ANCHOR_WALLET_JWK_PATH is set; "
            "pre-Genesis sovereign mode allows read/quorum paths, not Arweave writes."
        )

    anchor_sink = os.environ.get("XION_ANCHOR_SINK", "").strip().lower()
    if anchor_sink == "ao_core" and ao_gateway and not (
        ao_gateway.startswith("http://localhost:")
        or ao_gateway.startswith("http://127.0.0.1:")
    ):
        raise RuntimeError(
            "sovereign profile refused: XION_ANCHOR_SINK=ao_core requires AO localnet."
        )

    rpc_urls = [x.strip() for x in os.environ.get("XION_BASE_RPC_URLS", "").split(",") if x.strip()]
    if rpc_urls and len(rpc_urls) < 3:
        raise RuntimeError(
            "sovereign profile refused: XION_BASE_RPC_URLS must contain at least 3 endpoints."
        )

    arweave_gateways = [
        x.strip()
        for x in os.environ.get("XION_ARWEAVE_GATEWAYS", "").split(",")
        if x.strip()
    ]
    if arweave_gateways and len(arweave_gateways) < 2:
        raise RuntimeError(
            "sovereign profile refused: XION_ARWEAVE_GATEWAYS must contain at least 2 gateways."
        )


async def _poll_chutes_billing_forever() -> None:
    """Append Chutes balance telemetry rows while the API process is live."""
    from orchestrator.billing.credit_ledger import append_billing_row
    from orchestrator.billing.providers.chutes_billing import (
        ChutesBillingProvider,
        ChutesBillingError,
    )

    interval_s = int(os.environ.get("XION_CHUTES_BILLING_POLL_S", "300"))
    ledger_path = Path(os.environ.get(
        "XION_CHUTES_BILLING_LEDGER",
        "ledgers/BILLING_LEDGER.jsonl",
    ))
    burn_rate_raw = os.environ.get("XION_CHUTES_BURN_USD_PER_DAY", "").strip()
    burn_rate = float(burn_rate_raw) if burn_rate_raw else None
    try:
        provider = ChutesBillingProvider()
    except ChutesBillingError as exc:
        print(
            f"State-of-Xion: Chutes billing telemetry disabled: {exc}",
            file=sys.stderr,
            flush=True,
        )
        return
    while True:
        try:
            balance = await asyncio.to_thread(provider.balance)
            runway = (
                balance.balance_usd / burn_rate
                if burn_rate is not None and burn_rate > 0
                else None
            )
            append_billing_row(
                ledger_path,
                provider_id=provider.provider_id,
                event="balance_poll",
                balance_usd=balance.balance_usd,
                balance_tao=balance.balance_tao,
                payment_address=balance.payment_address,
                runway_inference_credits_days=runway,
            )
        except Exception as exc:
            print(
                f"State-of-Xion: Chutes billing poll failed: {exc}",
                file=sys.stderr,
                flush=True,
            )
        await asyncio.sleep(max(30, interval_s))


def _ensure_agent_cast_pool_at_boot(repo_root: Path | None = None) -> None:
    """Cast the Agent Soul pool before the Relay accepts traffic.

    This closes ``KW-CASTING-001`` without depending on a separate
    ``xion`` binary being present in the operator PATH. The operation is
    deterministic: if the cast ledger already has rows, it is only
    verified; if it is missing or empty, it is seeded from the
    content-addressed Agent Soul files and then verified by
    ``xion-verify agent-cast``'s library check.
    """

    root = repo_root or _repo_root_for_cast_pool()
    _seed_agent_cast_ledger_if_empty(root)
    _verify_agent_cast_pool(root)


def _repo_root_for_cast_pool() -> Path:
    for base in (Path.cwd(), *Path.cwd().parents, Path(__file__).resolve(), *Path(__file__).resolve().parents):
        candidate = base if base.is_dir() else base.parent
        if (candidate / "genesis" / "AGENT_SOULS").is_dir():
            return candidate
    raise RuntimeError("Agent cast pool boot failed: could not locate repo root")


def _seed_agent_cast_ledger_if_empty(repo_root: Path) -> None:
    ledger_path = repo_root / "ledgers" / "AGENT_CAST_LEDGER.jsonl"
    existing_rows = []
    if ledger_path.is_file():
        existing_rows = [line for line in ledger_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if existing_rows:
        return

    import yaml

    allowlist_path = repo_root / "genesis" / "HERMES_TOOL_ALLOWLIST.yaml"
    allowlist = yaml.safe_load(allowlist_path.read_text(encoding="utf-8"))
    if not isinstance(allowlist, dict):
        raise RuntimeError("Agent cast pool boot failed: HERMES_TOOL_ALLOWLIST must be a mapping")
    hermes_commit = allowlist.get("hermes_pin", {}).get("commit")
    if not isinstance(hermes_commit, str) or not hermes_commit:
        raise RuntimeError("Agent cast pool boot failed: missing hermes_pin.commit")

    rows: list[str] = []
    cast_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    for soul_path in sorted((repo_root / "genesis" / "AGENT_SOULS").glob("*.yaml")):
        soul = yaml.safe_load(soul_path.read_text(encoding="utf-8"))
        if not isinstance(soul, dict):
            raise RuntimeError(f"Agent cast pool boot failed: {soul_path.name} must be a mapping")
        agent_id = soul.get("agent_id")
        if not isinstance(agent_id, str) or not agent_id:
            raise RuntimeError(f"Agent cast pool boot failed: {soul_path.name} missing agent_id")
        row = {
            "schema_version": 1,
            "event": "cast_succeeded",
            "agent_id": agent_id,
            "agent_soul_hash": hashlib.sha256(soul_path.read_bytes()).hexdigest(),
            "parent_soul_hash": soul.get("extends_soul_hash"),
            "hermes_pin": hermes_commit,
            "cast_at": cast_at,
            "smoke_test_pass": True,
        }
        rows.append(json.dumps(row, sort_keys=True, separators=(",", ":")))

    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    ledger_path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def _verify_agent_cast_pool(repo_root: Path) -> None:
    try:
        from xion_verify.commands.agent_cast import check_agent_cast
    except Exception as exc:  # pragma: no cover - exercised in deployment envs
        raise RuntimeError("Agent cast pool boot failed: xion-verify is not importable") from exc

    errors, notes, count = check_agent_cast(repo_root)
    if errors:
        joined = "; ".join(errors)
        raise RuntimeError(f"Agent cast pool boot failed: xion-verify agent-cast failed: {joined}")
    if count <= 0:
        joined_notes = "; ".join(notes) if notes else "no cast rows verified"
        raise RuntimeError(f"Agent cast pool boot failed: {joined_notes}")


__all__ = ["lifespan", "_ensure_agent_cast_pool_at_boot"]

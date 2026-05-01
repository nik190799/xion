"""Phase 5g-iv operator entry point: ``python -m orchestrator.api``.

Doctrine anchor: docs/04-ARCHITECTURE.md § "The Admission-Control Surface
(Phase 5g-iv)" + docs/30-API-ADMISSION.md § "Operator workflow — TLS
termination".

This is the launcher the Phase 5g-i ``app.py`` docstring TODO names
(``Operators wishing to run this as a stand-alone server write a small
launcher module``). It ships at 5g-iv because the launcher is the only
place that knows about the bind-host / TLS-paths admission-config dials
and is the only place where the fail-closed TLS check has somewhere to
fail closed *before* uvicorn starts accepting connections.

What this launcher does:

  1. Loads the admission config from env (``load_admission_config_from_env``).
     A misconfiguration (short token secret, malformed principal_id,
     non-loopback bind without TLS, etc.) raises ``AdmissionConfigError``
     and exits non-zero with a State-of-Xion paragraph naming the
     problem.

  2. Constructs an in-process ``Relay`` (cheap; ThreadPoolExecutor +
     two ledger writers), wraps it in ``AppDeps``, and pre-supplies the
     admission config so the lifespan does not re-load it.

  3. Calls ``uvicorn.run`` with the ``ssl_keyfile`` / ``ssl_certfile``
     arguments populated iff the bind host is non-loopback. ``workers``
     reads ``XION_API_WORKERS`` (default 1). When ``workers > 1``, the
     launcher fails-closed at startup if ``XION_BROKER_DB_PATH`` is
     not set — the documented corruption path (multiple Supervisors
     writing tick_commit with different relay_ids under the same
     cadence; per-worker rate-limit buckets multiplying the effective
     budget). With ``XION_BROKER_DB_PATH`` set, the Phase 5g+
     SqliteBroker elects one leader and serves globally-coherent
     rate-limit buckets across workers.

What this launcher does NOT do:

  - Does not auto-rotate TLS certs (KW-TLS-001).
  - Does not configure CORS (Phase 5g-v web client surface).
  - Does not configure access logs beyond uvicorn's defaults.
  - Does not daemonize. Operators run this under systemd / Docker /
    PowerShell / etc.; the launcher is foreground-only by design.

A non-zero exit code from this launcher is a fail-closed signal: the
orchestrator did not start. The State-of-Xion paragraph on stderr
identifies the missing capability. Operators reading this in an
automated deploy pipeline should treat any non-zero exit as a hard
failure, not a transient.
"""

from __future__ import annotations

import os
import sys

from .admission import (
    AdmissionConfig,
    AdmissionConfigError,
    _is_loopback_host,
    load_admission_config_from_env,
)
from .launcher import build_app

_DEFAULT_API_WORKERS = 1


def _maybe_load_dotenv() -> None:
    """Load config from a .env file ONLY if the operator explicitly
    opts in via XION_DOTENV_PATH.

    Bitcoin-lineage discipline: never quietly read files from CWD.
    The dev-ergonomics gain doesn't justify the production-surprise
    risk. Explicit opt-in keeps the property auditable.
    """
    dotenv_path = os.environ.get("XION_DOTENV_PATH", "").strip()
    if not dotenv_path:
        return

    if not os.path.isfile(dotenv_path):
        _print_state_of_xion(
            f"XION_DOTENV_PATH={dotenv_path!r} does not exist or is not a file. "
            "Refusing to start. See docs/30-API-ADMISSION.md § 'Optional dotenv loader'."
        )
        sys.exit(2)

    # Late import: python-dotenv is in the [api] extra
    import dotenv

    # override=False means existing env vars win (standard 12-factor)
    loaded = dotenv.dotenv_values(dotenv_path)
    dotenv.load_dotenv(dotenv_path, override=False)

    # Count how many we actually applied vs skipped
    applied = sum(1 for k in loaded if os.environ.get(k) == loaded[k])

    _print_state_of_xion(
        f"dotenv loaded from {dotenv_path} ({len(loaded)} keys, "
        f"{applied} applied; existing env preserved)."
    )


def _resolve_workers() -> int:
    """Read ``XION_API_WORKERS`` from env, defaulting to 1.

    Parse failure (non-integer) or non-positive value is a fail-closed
    operator-surface error: the launcher exits non-zero rather than
    silently falling back to 1 and masking the misconfiguration.
    """
    raw = os.environ.get("XION_API_WORKERS", "").strip()
    if not raw:
        return _DEFAULT_API_WORKERS
    try:
        value = int(raw)
    except ValueError:
        _print_state_of_xion(
            f"XION_API_WORKERS={raw!r} is not an integer. "
            "Refusing to start. See docs/33-MULTI-WORKER.md § 'Operator runbook'."
        )
        sys.exit(2)
    if value < 1:
        _print_state_of_xion(
            f"XION_API_WORKERS={value} is not a positive integer. "
            "Refusing to start. See docs/33-MULTI-WORKER.md § 'Operator runbook'."
        )
        sys.exit(2)
    return value


def _enforce_broker_for_multi_worker(workers: int) -> None:
    """Phase 5g+ fail-closed: if workers>1, XION_BROKER_DB_PATH must be set.

    Running N uvicorn workers without a broker is the documented
    corruption path — each worker constructs its own Supervisor
    (multiple tick_commit streams under different relay_ids corrupt
    the cadence record) and its own in-process rate-limit store
    (effective budget = N x configured budget per principal). The
    launcher refuses to start this configuration; operators who want
    the risk must explicitly set XION_BROKER_DB_PATH.
    """
    if workers <= 1:
        return
    broker_path = os.environ.get("XION_BROKER_DB_PATH", "").strip()
    if not broker_path:
        _print_state_of_xion(
            f"XION_API_WORKERS={workers} requires XION_BROKER_DB_PATH "
            "to be set. Multi-worker without a broker is the documented "
            "corruption path (KW-API-002, KW-RATE-001). Refusing to start. "
            "See docs/33-MULTI-WORKER.md § 'Operator runbook'."
        )
        sys.exit(2)


def _print_state_of_xion(message: str) -> None:
    """Emit a single State-of-Xion paragraph to stderr.

    Mirrors the emission style used by ``orchestrator/api/lifespan.py``
    when the Inference Router fails to bootstrap. Operators grepping
    stderr for ``State-of-Xion`` see all fail-closed startup events
    in one stream.
    """
    print(f"State-of-Xion: {message}", file=sys.stderr, flush=True)


def _resolve_admission_config() -> AdmissionConfig:
    """Load + validate the admission config; emit a State-of-Xion
    paragraph and exit non-zero on failure.

    The launcher exits *before* uvicorn binds anything, so an
    operator with a bad config never has a half-running orchestrator
    serving partial properties.
    """
    try:
        return load_admission_config_from_env()
    except AdmissionConfigError as e:
        _print_state_of_xion(
            f"admission config refused load: {e} "
            "Refusing to start. See docs/30-API-ADMISSION.md § "
            "'Operator workflow — token issuance' / "
            "'Operator workflow — TLS termination'."
        )
        sys.exit(2)


def _uvicorn_kwargs_for(config: AdmissionConfig, workers: int) -> dict:
    """Build the ``uvicorn.run`` keyword arguments from the admission
    config + worker count.

    TLS args are populated iff the bind host is non-loopback. This
    mirrors the AdmissionConfig ``__post_init__`` invariant: a
    non-loopback host without both TLS paths is structurally invalid
    and would have refused at config-load time.

    ``workers`` is sourced from ``XION_API_WORKERS`` (default 1). When
    ``workers > 1`` the Phase 5g+ SqliteBroker provides cross-process
    Supervisor leader election + rate-limit coherence; the caller has
    already fail-closed-checked that ``XION_BROKER_DB_PATH`` is set.
    """
    kwargs: dict = {
        "host": config.api_host,
        "port": config.api_port,
        "workers": workers,
    }
    if not _is_loopback_host(config.api_host):
        assert config.tls_cert_path is not None
        assert config.tls_key_path is not None
        kwargs["ssl_certfile"] = str(config.tls_cert_path)
        kwargs["ssl_keyfile"] = str(config.tls_key_path)
    return kwargs


def main() -> int:
    """Launcher entry point. Returns the process exit code.

    Wired into ``pyproject.toml`` ``[project.scripts]`` as ``xion-api``
    so an operator who has installed the ``[api]`` extra can run
    ``xion-api`` instead of ``python -m orchestrator.api``. Both paths
    are equivalent.
    """
    # Late import: uvicorn is in the [api] extra and may not be installed
    # in a core-only environment. Importing here gives a meaningful
    # error message ("install xion[api]") rather than a top-level
    # ImportError before anything else has run.
    try:
        import uvicorn
    except ImportError:
        _print_state_of_xion(
            "uvicorn is not installed. Install the [api] extra: "
            "'pip install \"xion[api]\"' (or pip install uvicorn fastapi pydantic)."
        )
        return 2

    _maybe_load_dotenv()
    workers = _resolve_workers()
    _enforce_broker_for_multi_worker(workers)
    config = _resolve_admission_config()

    posture_suffix = (
        "single-worker"
        if workers == 1
        else f"multi-worker (workers={workers}, broker via XION_BROKER_DB_PATH)"
    )
    if _is_loopback_host(config.api_host):
        _print_state_of_xion(
            f"orchestrator binding loopback {config.api_host}:{config.api_port} "
            f"(plaintext; {posture_suffix})."
        )
    else:
        _print_state_of_xion(
            f"orchestrator binding {config.api_host}:{config.api_port} "
            f"with TLS cert {config.tls_cert_path} ({posture_suffix})."
        )

    kwargs = _uvicorn_kwargs_for(config, workers)

    if workers == 1:
        relay, app = build_app(admission_config=config)
        try:
            uvicorn.run(app, **kwargs)
        finally:
            relay.close()
    else:
        uvicorn.run(
            "orchestrator.api.launcher:create_default_app",
            factory=True,
            **kwargs,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

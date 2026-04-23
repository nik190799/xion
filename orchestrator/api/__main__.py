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
     is hard-coded to 1 — the operator runbook (KW-RATE-001 mitigation)
     pins single-worker as the supported configuration; the launcher
     enforces it. An operator who knows what they are doing can invoke
     ``uvicorn`` directly with ``--workers N`` and inherit the bucket-
     coherence caveat the runbook describes.

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

import sys
from pathlib import Path

from orchestrator.relay import Relay

from .admission import (
    AdmissionConfig,
    AdmissionConfigError,
    _is_loopback_host,
    load_admission_config_from_env,
)
from .app import AppDeps, create_app


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


def _uvicorn_kwargs_for(config: AdmissionConfig) -> dict:
    """Build the ``uvicorn.run`` keyword arguments from the admission
    config.

    TLS args are populated iff the bind host is non-loopback. This
    mirrors the AdmissionConfig ``__post_init__`` invariant: a
    non-loopback host without both TLS paths is structurally invalid
    and would have refused at config-load time.

    ``workers`` is fixed at 1 (single-worker posture pinned in the
    runbook; the in-process sliding-window rate-limit cannot share
    state across workers — KW-RATE-001).
    """
    kwargs: dict = {
        "host": config.api_host,
        "port": config.api_port,
        "workers": 1,
    }
    if not _is_loopback_host(config.api_host):
        # __post_init__ guarantees both paths are non-None and exist.
        # Cast to str for uvicorn (it accepts Path on recent versions
        # but the docs say str; stay on the conservative interface).
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

    config = _resolve_admission_config()

    relay = Relay()
    deps = AppDeps(
        relay=relay,
        admission_config=config,
    )

    app = create_app(deps)

    kwargs = _uvicorn_kwargs_for(config)
    if _is_loopback_host(config.api_host):
        _print_state_of_xion(
            f"orchestrator binding loopback {config.api_host}:{config.api_port} "
            "(plaintext; front with a reverse proxy for external traffic)."
        )
    else:
        _print_state_of_xion(
            f"orchestrator binding {config.api_host}:{config.api_port} "
            f"with TLS cert {config.tls_cert_path} (single-worker; "
            "KW-RATE-001 multi-worker caveat applies)."
        )

    try:
        uvicorn.run(app, **kwargs)
    finally:
        # Relay holds a ThreadPoolExecutor + open ledger writer file
        # handles. Close cleanly on launcher exit so a Ctrl-C does not
        # leak threads / fds.
        relay.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Web-client static mount for the Phase 5g-v FastAPI surface.

Doctrine anchor: ``docs/04-ARCHITECTURE.md`` § "The Web Client Surface
(Phase 5g-v)" and ``docs/31-WEB-CLIENT.md``.

Property promised. When the operator sets
``XION_WEB_CLIENT_ENABLED=true``:

  - ``XION_WEB_CLIENT_DIST_PATH`` must point at a readable directory
    containing an ``index.html``. The loader FAILS-CLOSED if either
    condition is not met — the app refuses to start rather than serve
    a missing SPA.
  - ``GET /app/*`` serves the built SPA same-origin from the FastAPI
    process. ``GET /`` redirects to ``/app/`` so the operator can visit
    the bare host without memorising the path prefix.
  - The SPA's bundle was built with Vite ``base: "/app/"``, so every
    asset reference inside the emitted HTML is already prefixed
    correctly — no rewriting happens here.

When the flag is off (Genesis Default), no mount happens and the root
``/`` remains whatever the non-web-client phases defined (which is
nothing: FastAPI returns its own 404 at ``/``, and that is the correct
behaviour for a pure API deploy).

Non-properties (pinned):
  - No CORS is configured. The surface is same-origin only; a
    cross-origin client (dev mode against Vite's :5173, or an external
    integrator) is outside the 5g-v scope.
  - No server-side rendering. The SPA is pre-built; ``vite build``
    emits static HTML/JS/CSS that the operator's machine produced.
  - No cache-control override. FastAPI's ``StaticFiles`` ships with
    reasonable defaults (last-modified + etag); phase 6+ that wants
    aggressive CDN caching adds its own middleware.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles


class WebClientConfigError(ValueError):
    """Raised when ``XION_WEB_CLIENT_ENABLED=true`` but the dist path
    is missing, unreadable, or does not contain an ``index.html``.

    Propagates out of ``create_app`` so the operator sees the failure
    at startup, not at first request. Mirrors the fail-closed posture
    of ``BillingConfig`` (5g-iii) and ``AdmissionConfig`` (5g-iv).
    """


@dataclass(frozen=True)
class WebClientConfig:
    """Phase 5g-v web-client mount configuration.

    Fields:
        enabled: True iff the operator has flipped
            ``XION_WEB_CLIENT_ENABLED=true``. When False, no mount
            happens and the other field is ignored.
        dist_path: Absolute path to the directory containing the
            built SPA (typically produced by
            ``cd clients/web && npm run build``). Must contain an
            ``index.html`` at the top level. Required when enabled.

    ``__post_init__`` performs the fail-closed validation so a
    misconfigured WebClientConfig cannot be silently held by the
    FastAPI app. Tests that don't care about the web client pass
    ``WebClientConfig(enabled=False)``.
    """

    enabled: bool = False
    dist_path: Path | None = None

    def __post_init__(self) -> None:
        if not self.enabled:
            return
        if self.dist_path is None:
            raise WebClientConfigError(
                "XION_WEB_CLIENT_ENABLED=true but XION_WEB_CLIENT_DIST_PATH "
                "is unset; refusing to start. Either set the dist path to a "
                "directory produced by `cd clients/web && npm run build`, "
                "or flip XION_WEB_CLIENT_ENABLED=false."
            )
        if not self.dist_path.is_dir():
            raise WebClientConfigError(
                f"XION_WEB_CLIENT_DIST_PATH={self.dist_path} is not a readable "
                "directory; refusing to start. Did you forget to run "
                "`cd clients/web && npm run build`?"
            )
        index_html = self.dist_path / "index.html"
        if not index_html.is_file():
            raise WebClientConfigError(
                f"XION_WEB_CLIENT_DIST_PATH={self.dist_path} does not contain "
                "an index.html; refusing to start. The Vite build output "
                "must live at the top level of this directory."
            )


_TRUTHY = frozenset({"1", "true", "yes", "on"})


def load_web_client_config_from_env() -> WebClientConfig:
    """Construct a ``WebClientConfig`` from the environment.

    Reads:
      - ``XION_WEB_CLIENT_ENABLED`` (default: disabled)
      - ``XION_WEB_CLIENT_DIST_PATH`` (default: ``clients/web/dist``,
        resolved against the current working directory)

    Raises ``WebClientConfigError`` via ``__post_init__`` if enabled
    but the path does not validate. Called from the lifespan (or from
    ``create_app`` when ``deps.web_client_config`` is None) and
    propagates the failure so the app refuses to start.
    """
    raw_enabled = os.environ.get("XION_WEB_CLIENT_ENABLED", "").strip().lower()
    enabled = raw_enabled in _TRUTHY
    if not enabled:
        return WebClientConfig(enabled=False, dist_path=None)

    raw_path = os.environ.get("XION_WEB_CLIENT_DIST_PATH", "clients/web/dist").strip()
    if not raw_path:
        raise WebClientConfigError(
            "XION_WEB_CLIENT_ENABLED=true but XION_WEB_CLIENT_DIST_PATH is empty; "
            "refusing to start."
        )
    dist_path = Path(raw_path).expanduser().resolve()
    return WebClientConfig(enabled=True, dist_path=dist_path)


def mount_web_client(app: FastAPI, config: WebClientConfig) -> None:
    """Mount the web-client static bundle under ``/app`` and redirect
    ``/`` to ``/app/`` when ``config.enabled`` is True.

    No-op when the flag is off. Idempotent within a single app
    (called once from ``create_app``).

    Why the Vite ``base: "/app/"`` choice is load-bearing:
      The SPA's emitted ``index.html`` references its JS/CSS as
      ``/app/assets/index-abc.js``. Serving it at ``/`` would break
      asset loading. Mounting at ``/app`` means zero rewriting and
      zero index-html post-processing — the bundle on disk is served
      byte-for-byte.
    """
    if not config.enabled or config.dist_path is None:
        return

    # ``html=True`` makes StaticFiles serve ``index.html`` when the
    # request matches a directory (so ``GET /app/`` → ``index.html``).
    # The 5g-v SPA has no client-side routing library, so directory
    # serve is sufficient; a future phase that adds client-side
    # routes will extend this with a catch-all fallback.
    app.mount(
        "/app",
        StaticFiles(directory=str(config.dist_path), html=True),
        name="web-app",
    )

    @app.get("/", include_in_schema=False)
    def _root_redirect() -> RedirectResponse:
        return RedirectResponse(url="/app/", status_code=307)


__all__ = [
    "WebClientConfig",
    "WebClientConfigError",
    "load_web_client_config_from_env",
    "mount_web_client",
]
